"""Functions for creating internal model representations of settings from EpiViz
"""
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy.special import logit
from scipy import interpolate
from scipy import spatial

import intervals as it

from cascade.input_data.configuration.id_map import PRIMARY_INTEGRANDS_TO_RATES, make_integrand_map
from cascade.model.covariates import Covariate, CovariateMultiplier
from cascade.model.grids import AgeTimeGrid, PriorGrid
from cascade.model.rates import Smooth
from cascade.input_data.configuration import SettingsError
from cascade.input_data.db.ccov import country_covariates
from cascade.input_data.db.demographics import get_all_age_spans
from cascade.core.context import ModelContext
import cascade.model.priors as priors
from cascade.input_data import InputDataError

from cascade.core.log import getLoggers
CODELOG, MATHLOG = getLoggers(__name__)


def identity(x):
    return x


def squared(x):
    return np.power(x, 2)


def scale1000(x):
    return x * 1000


COVARIATE_TRANSFORMS = {0: identity, 1: np.log, 2: logit, 3: squared, 4: np.sqrt, 5: scale1000}
"""
These functions transform covariate data, as specified in EpiViz.
"""


class SettingsToModelError(InputDataError):
    """Error creating a model from the settings"""


def initial_context_from_epiviz(configuration):
    context = ModelContext()
    context.parameters.modelable_entity_id = configuration.model.modelable_entity_id
    context.parameters.bundle_id = configuration.model.bundle_id
    context.parameters.gbd_round_id = configuration.gbd_round_id
    context.parameters.location_id = configuration.model.drill_location
    context.parameters.rate_case = configuration.model.rate_case
    context.parameters.minimum_meas_cv = configuration.model.minimum_meas_cv

    return context


def unique_country_covariate_transform(configuration):
    """
    Iterates through all covariate IDs, including the list of ways to
    transform them, because each transformation is its own column for Dismod.
    """
    seen_covariate = defaultdict(set)
    if configuration.country_covariate:
        for covariate_configuration in configuration.country_covariate:
            seen_covariate[covariate_configuration.country_covariate_id].add(covariate_configuration.transformation)

    for cov_id, cov_transformations in seen_covariate.items():
        yield cov_id, list(sorted(cov_transformations))


def assign_covariates(model_context, execution_context, configuration):
    """
    The EpiViz interface allows assigning a covariate with a transformation
    to a specific target (rate, measure value, measure standard deviation).
    There will be one Dismod-AT covariate for each (input covariate dataset,
    transformation of that dataset).

    Args:
        model_context (ModelContext): model context that has age groups.
            The context is modified by this function. Covariate columns are
            added to input data and covariates are added to the list of
            covariates.
        execution_context: For the gbd_round_id.
        configuration (Configuration): Holds settings from EpiViz form.

    Returns:
        function:
            This function is a map from the covariate identifier in the
            settings to the covariate name.

    The important choices are assignment of covariates to observations and
    integrands by
    :py:func:`covariate_to_measurements_nearest_favoring_same_year`
    and how reference values are chosen by
    :py:func:`reference_value_for_covariate_mean_all_values`.
    """
    covariate_map = {}  # to find the covariates for covariate multipliers.
    avgint_table = model_context.average_integrand_cases
    age_groups = get_all_age_spans(model_context)

    # This walks through all unique combinations of covariates and their
    # transformations. Then, later, we apply them to particular target
    # rates, meas_values, meas_stds.
    for country_covariate_id, transforms in unique_country_covariate_transform(configuration):
        demographics = dict(
            age_group_ids="all", year_ids="all", sex_ids="all", location_ids=[model_context.parameters.location_id]
        )
        ccov_df = country_covariates(country_covariate_id, demographics, execution_context.parameters.gbd_round_id)
        covariate_name = ccov_df.loc[0]["covariate_name_short"]

        # There is an order dependency from whether we interpolate before we
        # transform or transform before we interpolate.

        # Decide how to take the given data and extend / subset / interpolate.
        ccov_ranges_df = convert_gbd_ids_to_dismod_values(ccov_df, age_groups)

        if model_context.input_data.observations is not None:
            MATHLOG.info(f"Adding {country_covariate_id} using "
                         f"covariate_to_measurements_nearest_favoring_same_year()")
            observations_column = covariate_to_measurements_nearest_favoring_same_year(
                model_context.input_data.observations, ccov_ranges_df)
        else:
            observations_column = None
        if avgint_table is not None:
            avgint_column = covariate_to_measurements_nearest_favoring_same_year(
                avgint_table, ccov_ranges_df)
        else:
            avgint_column = None

        for transform in transforms:
            # This happens per application to integrand.
            settings_transform = COVARIATE_TRANSFORMS[transform]
            transform_name = settings_transform.__name__
            MATHLOG.info(f"Transforming {covariate_name} with {transform_name}")
            name = f"{covariate_name}_{transform_name}"

            # The reference value is calculated from the download, not from the
            # the download as applied to the observations.
            reference = reference_value_for_covariate_mean_all_values(settings_transform(ccov_df))
            covariate_obj = Covariate(name, reference)
            model_context.input_data.covariates.append(covariate_obj)
            covariate_map[(country_covariate_id, transform)] = covariate_obj

            # Now attach the column to the observations.
            if observations_column is not None:
                model_context.input_data.observations[f"x_{name}"] = settings_transform(observations_column)
            if avgint_column is not None:
                avgint_table[f"x_{name}"] = settings_transform(avgint_column)

    def column_id_func(covariate_search_id, transformation_id):
        return covariate_map[(covariate_search_id, transformation_id)]

    return column_id_func


def create_covariate_multipliers(context, configuration, column_id_func):
    """
    Reads settings to create covariate multipliers. This attaches a
    covariate column with its reference value to a smooth grid
    and applies it to a rate value, integrand value, or integrand
    standard deviation. There aren't a lot of interesting choices in here.

    Args:
        context:
        configuration:
        column_id_func:
    """
    # Assumes covariates exist.
    gbd_to_dismod_integrand_enum = make_integrand_map()

    for mul_cov_config in configuration.country_covariate:
        smooth = make_smooth(configuration, mul_cov_config)
        covariate_obj = column_id_func(mul_cov_config.country_covariate_id, mul_cov_config.transformation)
        covariate_multiplier = CovariateMultiplier(covariate_obj, smooth)
        if mul_cov_config.measure_id not in gbd_to_dismod_integrand_enum:
            raise RuntimeError(f"The measure id isn't recognized as an integrand {mul_cov_config.measure_id}")
        target_dismod_name = gbd_to_dismod_integrand_enum[mul_cov_config.measure_id].name
        if mul_cov_config.mulcov_type == "rate_value":
            if target_dismod_name not in PRIMARY_INTEGRANDS_TO_RATES:
                raise SettingsToModelError(
                    f"Multiplier type for covariate {mul_cov_config.country_covariate_id} is on the rate value. "
                    f"Can only set a rate value on a primary integrand. Measure id "
                    f"{mul_cov_config.measure_id} name {target_dismod_name} is not a primary integrand. "
                    f"Primary integrands are {', '.join(list(sorted(PRIMARY_INTEGRANDS_TO_RATES.keys())))}"
                )
            target_rate = PRIMARY_INTEGRANDS_TO_RATES[target_dismod_name]
            MATHLOG.info(f"Covariate multiplier for measure_id {mul_cov_config.measure_id} applied to rate {target_rate} "
                         f"It was set to primary integrand {target_dismod_name} in EpiViz.")
            add_to_rate = getattr(context.rates, target_rate)
            add_to_rate.covariate_multipliers.append(covariate_multiplier)
        else:
            add_to_integrand = context.integrand_covariate_multipliers[target_dismod_name]
            if mul_cov_config.mulcov_type == "meas_value":
                add_to_integrand.value_covariate_multipliers.append(covariate_multiplier)
            elif mul_cov_config.mulcov_type == "meas_std":
                add_to_integrand.std_covariate_multipliers.append(covariate_multiplier)
            else:
                raise RuntimeError(f"mulcov_type isn't among the three {configuration.mulcov_type}")


def reference_value_for_covariate_mean_all_values(cov_df):
    """
    Strategy for choosing reference value for country covariate.
    This one takes the mean of all incoming covariate values.
    """
    return float(cov_df["mean_value"].mean())


def covariate_to_measurements_nearest_favoring_same_year(measurements, covariates):
    """
    Given a covariate that might not cover all of the age and time range
    of the measurements select a covariate value for each measurement.
    This version chooses the covariate value whose mean age and time
    is closest to the mean age and time of the measurement in the same
    year. If that isn't found, it picks the covariate that is closest
    in age and time in the nearest year. In the case of a tie for distance,
    it averages.

    Args:
        measurements (pd.DataFrame):
            Columns include ``age_lower``, ``age_upper``, ``time_lower``,
            ``time_upper``. All others are ignored.
        covariates (pd.DataFrame):
            Columns include ``age_lower``, ``age_upper``, ``time_lower``,
            ``time_upper``, and ``value``.

    Returns:
        pd.Series: One row for every row in the measurements.
    """
    if measurements is None: return
    # Rescaling the age means that the nearest age within the year
    # will always be closer than the nearest time across a full year.
    tree = spatial.KDTree(
        list(
            zip(
                covariates[["age_lower", "age_upper"]].mean(axis=1) / 240,
                covariates[["time_lower", "time_upper"]].mean(axis=1),
                covariates["x_sex"],
            )
        )
    )
    _, indices = tree.query(
        list(
            zip(
                measurements[["age_lower", "age_upper"]].mean(axis=1) / 240,
                measurements[["time_lower", "time_upper"]].mean(axis=1),
                measurements["x_sex"],
            )
        )
    )
    return pd.Series(covariates.iloc[indices]["mean_value"].values, index=measurements.index)


def convert_gbd_ids_to_dismod_values(with_ids_df, age_groups_df):
    """
    Converts ``age_group_id`` into ``age_lower`` and ``age_upper`` and
    ``year_id`` into ``time_lower`` and ``time_upper``. This treats the year
    as a range from start of year to start of the next year.
    Also converts sex_id=[1, 2, 3] into x_sex=[0.5, -0.5, 0].

    Args:
        with_ids_df (pd.DataFrame): Has ``age_group_id`` and ``year_id``.
        age_groups_df (pd.DataFrame): Has columns ``age_group_id``,
            ``age_group_years_start``, and ``age_group_years_end``.

    Returns:
        pd.DataFrame: New pd.DataFrame with four added columns and in the same
            order as the input dataset.
    """
    sex_df = pd.DataFrame(dict(x_sex=[-0.5, 0, 0.5], sex_id=[2, 3, 1]))
    original_order = with_ids_df.copy()
    # This "original index" guarantees that the order of the output dataset
    # and the index of the output dataset match that of with_ids_df, because
    # the merge reorders everything, including creation of a new index.
    original_order["original_index"] = original_order.index
    aged = pd.merge(original_order, age_groups_df, on="age_group_id", sort=False)
    merged = pd.merge(aged, sex_df, on="sex_id")
    if len(merged) != len(with_ids_df):
        # This is a fault in the input data.
        incoming_age_group_ids = set(with_ids_df.age_group_id.unique())
        missing = incoming_age_group_ids - set(age_groups_df.age_group_id.unique())
        raise InputDataError(f"Not all age group ids from observations are found in the age group list "
                           f"missing age groups {missing} other age ids in bundle {list(sorted(incoming_age_group_ids))} "
                           f"Of the original {len(with_ids_df)} records, {len(merged)} had known ids.")
    reordered = merged.sort_values(by="original_index").reset_index()
    reordered["time_lower"] = reordered["year_id"]
    MATHLOG.info(f"Conversion of bundle assumes demographic notation for years, "
                 f"so it adds a year to time_upper.")
    reordered["time_upper"] = reordered["year_id"] + 1
    dropped = reordered.drop(columns=["age_group_id", "year_id", "original_index"])
    return dropped.rename(columns={"age_group_years_start": "age_lower", "age_group_years_end": "age_upper"})


def make_smooth(configuration, smooth_configuration):
    ages = smooth_configuration.age_grid
    if ages is None:
        if getattr(smooth_configuration, "rate", None) == "pini":
            ages = [0]
        else:
            ages = configuration.model.default_age_grid
    times = smooth_configuration.time_grid
    if times is None:
        times = configuration.model.default_time_grid
    grid = AgeTimeGrid(ages, times)

    d_time = PriorGrid(grid)
    d_age = PriorGrid(grid)
    value = PriorGrid(grid)

    if smooth_configuration.default.dage is None:
        d_age[:, :].prior = priors.Uniform(float("-inf"), float("inf"), 0)
    else:
        d_age[:, :].prior = smooth_configuration.default.dage.prior_object
    if smooth_configuration.default.dtime is None:
        d_time[:, :].prior = priors.Uniform(float("-inf"), float("inf"), 0)
    else:
        d_time[:, :].prior = smooth_configuration.default.dtime.prior_object
    value[:, :].prior = smooth_configuration.default.value.prior_object

    if smooth_configuration.detail:
        for row in smooth_configuration.detail:
            if row.prior_type == "dage":
                pgrid = d_age
            elif row.prior_type == "dtime":
                pgrid = d_time
            elif row.prior_type == "value":
                pgrid = value
            else:
                raise SettingsError(f"Unknown prior type {row.prior_type}")
            pgrid[slice(row.age_lower, row.age_upper), slice(row.time_lower, row.time_upper)].prior = row.prior_object
    return Smooth(value, d_age, d_time)


def fixed_effects_from_epiviz(model_context, execution_context, configuration):
    if configuration.rate:
        for rate_config in configuration.rate:
            rate_name = rate_config.rate
            if rate_name not in [r.name for r in model_context.rates]:
                raise SettingsError(f"Unspported rate {rate_name}")
            rate = getattr(model_context.rates, rate_name)
            rate.parent_smooth = make_smooth(configuration, rate_config)

    covariate_column_id_func = assign_covariates(model_context, execution_context, configuration)
    create_covariate_multipliers(model_context, configuration, covariate_column_id_func)


def random_effects_from_epiviz(model_context, configuration):
    if configuration.random_effect:
        for smoothing_config in configuration.random_effect:
            rate_name = smoothing_config.rate
            if rate_name not in [r.name for r in model_context.rates]:
                raise SettingsError(f"Unspported rate {rate_name}")
            rate = getattr(model_context.rates, rate_name)
            location = smoothing_config.location
            rate.child_smoothings.append((location, make_smooth(configuration, smoothing_config)))


def generate_covariate_interpolators_by_sex(covariates, covar_at_dims):
    """
    Generates an interpolator for each sex - female, male, and both sexes.

    Args:
        covariates (pd.DataFrame): data for one covariate
        covar_at_dims (dictionary): indicates if age and time are 1d (and not just a single point)

    Returns:
        Dictionary of interpolators, key = x_sex (-0.5, 0, 0.5)
    """

    interpolators = dict()

    female = -0.5
    male = 0.5
    both = 0

    sex_both = set([both])
    sex_fm = set([female, male])

    covars_sex = set(covariates["x_sex"].unique())

    # covariate is not by sex, and is identified as both_sexes
    if len(covars_sex) and covars_sex.issubset(sex_both):

        interpolator = select_interpolator_based_on_at_dims(covariates, covar_at_dims)

        interpolators[female] = interpolator
        interpolators[both] = interpolator
        interpolators[male] = interpolator

    # covariate is by sex, and exists for female and for male
    elif covars_sex.issubset(sex_fm) and covars_sex.issuperset(sex_fm):

        covariates_f = covariates[covariates["x_sex"] == female]
        covariates_m = covariates[covariates["x_sex"] == male]
        covariates_both = covariates_f.merge(
            covariates_m,
            on=["age_lower", "age_upper", "time_lower", "time_upper"],
            how="inner")
        covariates_both["mean_value"] = covariates_both[
            ["mean_value_x", "mean_value_y"]].mean(axis=1)

        interpolator_f = select_interpolator_based_on_at_dims(covariates_f, covar_at_dims)
        interpolator_m = select_interpolator_based_on_at_dims(covariates_m, covar_at_dims)
        interpolator_both = select_interpolator_based_on_at_dims(covariates_both, covar_at_dims)

        interpolators[female] = interpolator_f
        interpolators[male] = interpolator_m
        interpolators[both] = interpolator_both

    else:

        raise ValueError(f"""set of sexes in covariates is {covars_sex},
            expecting {sex_both} or {sex_fm}""")

    return interpolators


def assign_interpolated_covariate_values(measurements, covariates):
    """
    Compute a column of covariate values to assign to the measurements.

    Args:
        measurements (pd.DataFrame):
            Columns include ``age_lower``, ``age_upper``, ``time_lower``,
            ``time_upper``. All others are ignored.
        covariates (pd.DataFrame):
            Columns include ``age_lower``, ``age_upper``, ``time_lower``,
            ``time_upper``, ``sex``, and ``value``.
    Returns:
        pd.Series: One row for every row in the measurements.
    """

    # is the covariate by_age, does it have multiple years?
    covar_at_dims = compute_covariate_age_time_dimensions(covariates)

    # generate 1d or 2d interpolators by sex
    interpolators = generate_covariate_interpolators_by_sex(covariates, covar_at_dims)

    # identify the overall interval for the covariate ages, could have middle gaps
    covar_age_interval = compute_covariate_age_interval(covariates)

    # use interpolators to find a matching covariate value for each measurement
    covariate_column = compute_interpolated_covariate_values_by_sex(
        measurements, interpolators, covar_at_dims, covar_age_interval)

    return covariate_column


def select_interpolator_based_on_at_dims(covariates, covar_at_dims):
    """
    Create a 1d or a 2d interpolator based on the dimensions of age
    and time across the covariate data set.

    Returns: scipy.interpolator.interp1d or scipy.interpolator.interp2d
    """

    # neither age nor time are single values for entire covariate data set
    if covar_at_dims["age_1d"] and covar_at_dims["time_1d"]:

        interpolator = interpolate.interp2d(
            covariates[["age_lower", "age_upper"]].mean(axis=1),
            covariates[["time_lower", "time_upper"]].mean(axis=1),
            covariates["mean_value"])

    # time is a single value
    elif covar_at_dims["age_1d"] and not covar_at_dims["time_1d"]:

        interpolator = interpolate.interp1d(
            covariates[["age_lower", "age_upper"]].mean(axis=1),
            covariates["mean_value"], bounds_error=False)

    # age is a single value
    elif not covar_at_dims["age_1d"] and covar_at_dims["time_1d"]:

        interpolator = interpolate.interp1d(
            covariates[["time_lower", "time_upper"]].mean(axis=1),
            covariates["mean_value"], bounds_error=False)

    # both age and time have only one value for the entire covariate data set
    else:
        raise ValueError(f"""Both age and time have only one value for the entire
                         covariate data set, which is unexpected.""")

    return interpolator


def compute_covariate_age_time_dimensions(covariates):
    """
    Determines if the input covariate data is by_age and/or by_time.

    Returns:
        dictionary: keys indicate if age or time are points (0d) vs. 1d
    """

    covar_at_dims = {}

    covar_at_dims["age_1d"] = len(set(zip(covariates["age_lower"], covariates["age_upper"]))) > 1

    covar_at_dims["time_1d"] = len(set(zip(covariates["time_lower"], covariates["time_upper"]))) > 1

    return covar_at_dims


def compute_covariate_age_interval(covariates):
    """
    Create an interval expressing all the ages in the covariates data frame.
    If the covariates have age ranges like: [5,10], [10,15], [30,35], [35-80],
    the overall age interval would be: [5,15], [30,80]
    This allows checks like: 9.5 in age_interval (yes), 20.25 in age_interval (no),
    0.667 in age_interval (no), 95 in age_interval (no), 50.1 in age_interval (yes)

    Returns:
        Interval: of ages in the covariates data frame
    """
    age_interval = it.empty()

    age_groups = set(zip(covariates["age_lower"], covariates["age_upper"]))

    for age in age_groups:
        age_interval = age_interval | it.closed(age[0], age[1])

    return age_interval


def compute_interpolated_covariate_values_by_sex(
        measurements, interpolators, covar_at_dims, covar_age_interval):
    """
    Use the measurements data by sex as input to the corresponding interpolator
    to assign a covariate value to the measurement.

    Returns:
        pd.Series: One row for every row in the measurements.
    """

    female = -0.5
    male = 0.5
    both = 0

    measurements_f = measurements[measurements["x_sex"] == female]
    measurements_m = measurements[measurements["x_sex"] == male]
    measurements_both = measurements[measurements["x_sex"] == both]

    index_f = measurements_f.index.tolist()
    index_m = measurements_m.index.tolist()
    index_both = measurements_both.index.tolist()

    # covariate is by_age and "by_time"
    if covar_at_dims["age_1d"] and covar_at_dims["time_1d"]:

        covariate_f = [interpolators[female](age, time)[0] for age, time in
                       zip(measurements_f[["age_lower", "age_upper"]].mean(axis=1),
                           measurements_f[["time_lower", "time_upper"]].mean(axis=1))]

        covariate_m = [interpolators[male](age, time)[0] for age, time in
                       zip(measurements_m[["age_lower", "age_upper"]].mean(axis=1),
                           measurements_m[["time_lower", "time_upper"]].mean(axis=1))]

        covariate_both = [interpolators[both](age, time)[0] for age, time in
                          zip(measurements_both[["age_lower", "age_upper"]].mean(axis=1),
                              measurements_both[["time_lower", "time_upper"]].mean(axis=1))]

    # covariate is by_age, but not "by_time"
    elif covar_at_dims["age_1d"] and not covar_at_dims["time_1d"]:

        covariate_f = [interpolators[female](age).item()
                       for age in measurements_f[["age_lower", "age_upper"]].mean(axis=1)]

        covariate_m = [interpolators[male](age).item()
                       for age in measurements_m[["age_lower", "age_upper"]].mean(axis=1)]

        covariate_both = [interpolators[both](age).item()
                          for age in measurements_both[["age_lower", "age_upper"]].mean(axis=1)]

    # covariate is "by_time", but not by_age
    elif not covar_at_dims["age_1d"] and covar_at_dims["time_1d"]:

        covariate_f = [interpolators[female](time).item()
                       for time in measurements_f[["time_lower", "time_upper"]].mean(axis=1)]

        covariate_m = [interpolators[male](time).item()
                       for time in measurements_m[["time_lower", "time_upper"]].mean(axis=1)]

        covariate_both = [interpolators[both](time).item()
                          for time in measurements_both[["time_lower", "time_upper"]].mean(axis=1)]

    cov_col = []
    cov_index = []

    cov_col = covariate_f + covariate_m + covariate_both
    cov_index = index_f + index_m + index_both

    covariate_column = pd.Series(cov_col, index=cov_index).sort_index()

    # set missings using covar_age_interval

    meas_mean_age = measurements[["age_lower", "age_upper"]].mean(axis=1)
    meas_mean_age_in_age_interval = [i in covar_age_interval for i in meas_mean_age]
    covariate_column = pd.Series(np.where(meas_mean_age_in_age_interval, covariate_column, np.nan))

    return covariate_column
