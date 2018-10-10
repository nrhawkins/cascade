"""
    # Notes
    # tree = spatial.KDTree(list(zip(
    #   covariates[["age_lower", "age_upper"]].mean(axis=1) / 240,
    #   covariates[["time_lower", "time_upper"]].mean(axis=1),
    #    covariates["x_sex"]
    # )))

    # _, indices = tree.query(list(zip(
    #    measurements[["age_lower", "age_upper"]].mean(axis=1) / 240,
    #    measurements[["time_lower", "time_upper"]].mean(axis=1),
    #    measurements["x_sex"],
    # )))

    # covariates_m, covariates_f

    # x = covariates[["age_lower", "age_upper"]].mean(axis=1) / 240
    # y = covariates[["time_lower", "time_upper"]].mean(axis=1)

    # f = interpolate.interp2d(x, y, z)

    # return pd.Series(covariates.iloc[indices]["mean_value"].values, index=measurements.index)
"""

from scipy import interpolate
import intervals as it
import numpy as np
import pandas as pd


def generate_covariate_interpolators(covariates, covar_at_dims):
    """
    Args:

    Returns:
        Dictionary of interpolators, key = x_sex
    """

    interpolators = dict()

    both = 0
    male = 0.5
    female = -0.5

    sex_both = set([both])
    sex_mf = set([female, male])

    covars_sex = set(covariates["x_sex"].unique())

    if len(covars_sex) and covars_sex.issubset(sex_both):

        interpolator = select_interpolator(covariates, covar_at_dims)

        interpolators[female] = interpolator
        interpolators[both] = interpolator
        interpolators[male] = interpolator

    elif covars_sex.issubset(sex_mf) and covars_sex.issuperset(sex_mf):

        covariates_f = covariates[covariates["x_sex"] == female]
        covariates_m = covariates[covariates["x_sex"] == male]
        covariates_both = covariates_f.merge(
            covariates_m,
            on=["age_lower", "age_upper", "time_lower", "time_upper"],
            how="inner")
        covariates_both["mean_value"] = covariates_both[
            ["mean_value_x", "mean_value_y"]].mean(axis=1)

        interpolator_f = select_interpolator(covariates_f, covar_at_dims)
        interpolator_m = select_interpolator(covariates_m, covar_at_dims)
        interpolator_both = select_interpolator(covariates_both, covar_at_dims)

        interpolators[female] = interpolator_f
        interpolators[male] = interpolator_m
        interpolators[both] = interpolator_both

    else:

        raise ValueError(f"""set of sexes in covariates is {covars_sex},
            expecting {sex_both} or {sex_mf}""")

    return interpolators


def assign_interpolated_covariate_values(measurements, covariates):
    """
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

    covar_at_dims = compute_covariate_age_time_dimensions(covariates)

    interpolators = generate_covariate_interpolators(covariates, covar_at_dims)

    covar_age_interval = compute_covariate_age_interval(covariates)

    covariate_column = compute_interpolated_covariate_values(
        measurements, interpolators, covar_at_dims, covar_age_interval)

    return covariate_column


def select_interpolator(covariates, covar_at_dims):
    """
    """

    if covar_at_dims["age_2d"] and covar_at_dims["time_2d"]:

        interpolator = interpolate.interp2d(
            covariates[["age_lower", "age_upper"]].mean(axis=1),
            covariates[["time_lower", "time_upper"]].mean(axis=1),
            covariates["mean_value"])

    elif covar_at_dims["age_2d"] and not covar_at_dims["time_2d"]:

        interpolator = interpolate.interp1d(
            covariates[["age_lower", "age_upper"]].mean(axis=1),
            covariates["mean_value"], bounds_error=False)

    elif not covar_at_dims["age_2d"] and covar_at_dims["time_2d"]:

        interpolator = interpolate.interp1d(
            covariates[["time_lower", "time_upper"]].mean(axis=1),
            covariates["mean_value"], bounds_error=False)

    else:

        raise ValueError("Neither age nor time has 2 dimensions, so don't need to interpolate.")

    return interpolator


def compute_covariate_age_time_dimensions(covariates):

    covar_at_dims = {}

    covar_at_dims["age_2d"] = len(set(zip(covariates["age_lower"], covariates["age_upper"]))) > 1

    covar_at_dims["time_2d"] = len(set(zip(covariates["time_lower"], covariates["time_upper"]))) > 1

    return covar_at_dims


def compute_covariate_age_interval(covariates):
    """
    Create an interval expressing all the ages in the covariates data frame.
    This allows a check like: 9.5 in age_interval

    Returns:
        Interval of ages in the covariates data frame
    """
    age_interval = it.empty()

    # issue: [5,9], [10,14] or [5,10], [10,15], need the latter
    # may need to add one to age_upper
    age_groups = set(zip(covariates["age_lower"], covariates["age_upper"]))

    for age in age_groups:
        age_interval = age_interval | it.closed(age[0], age[1])

    return age_interval


def compute_interpolated_covariate_values(measurements, interpolators,
                                          covar_at_dims, covar_age_interval):

    female = -0.5
    male = 0.5
    both = 0

    measurements_f = measurements[measurements["x_sex"] == female]
    measurements_m = measurements[measurements["x_sex"] == male]
    measurements_both = measurements[measurements["x_sex"] == both]

    index_f = measurements_f.index
    index_m = measurements_m.index
    index_both = measurements_both.index

    if covar_at_dims["age_2d"] and covar_at_dims["time_2d"]:

        covariate_f = interpolators[female](
            measurements_f[["age_lower", "age_upper"]].mean(axis=1),
            measurements_f[["time_lower", "time_upper"]].mean(axis=1))

        covariate_m = interpolators[male](
            measurements_m[["age_lower", "age_upper"]].mean(axis=1),
            measurements_m[["time_lower", "time_upper"]].mean(axis=1))

        covariate_both = interpolators[both](
            measurements_both[["age_lower", "age_upper"]].mean(axis=1),
            measurements_both[["time_lower", "time_upper"]].mean(axis=1))

    elif covar_at_dims["age_2d"] and not covar_at_dims["time_2d"]:

        covariate_f = interpolators[female](
            measurements_f[["age_lower", "age_upper"]].mean(axis=1))

        covariate_m = interpolators[male](
            measurements_m[["age_lower", "age_upper"]].mean(axis=1))

        covariate_both = interpolators[both](
            measurements_both[["age_lower", "age_upper"]].mean(axis=1))

    elif not covar_at_dims["age_2d"] and covar_at_dims["time_2d"]:

        covariate_f = interpolators[female](
            measurements_f[["time_lower", "time_upper"]].mean(axis=1))

        covariate_m = interpolators[male](
            measurements_m[["time_lower", "time_upper"]].mean(axis=1))

        covariate_both = interpolators[both](
            measurements_both[["time_lower", "time_upper"]].mean(axis=1))

    cov_col = []
    cov_index = []

    if covariate_f.ndim == 1:
        cov_f = covariate_f
        cov_col = cov_col + list(cov_f)
        cov_index = cov_index + list(index_f)
    elif covariate_f.ndim == 2:
        cov_f = covariate_f[0]
        cov_col = cov_col + list(cov_f)
        cov_index = cov_index + list(index_f)

    if covariate_m.ndim == 1:
        cov_m = covariate_m
        cov_col = cov_col + list(cov_m)
        cov_index = cov_index + list(index_m)
    elif covariate_m.ndim == 2:
        cov_m = covariate_m[0]
        cov_col = cov_col + list(cov_m)
        cov_index = cov_index + list(index_m)

    if covariate_both.ndim == 1:
        cov_both = covariate_both
        cov_col = cov_col + list(cov_both)
        cov_index = cov_index + list(index_both)
    elif covariate_both.ndim == 2:
        cov_both = covariate_both[0]
        cov_col = cov_col + list(cov_both)
        cov_index = cov_index + list(index_both)

    covariate_column = pd.Series(cov_col, index=cov_index).sort_index()

    # set missings using covar_age_interval
    meas_mean_age = measurements[["age_lower", "age_upper"]].mean(axis=1)
    mean_age_in_age_interval = [i in covar_age_interval for i in meas_mean_age]
    covariate_column = pd.Series(np.where(mean_age_in_age_interval, covariate_column, np.nan))

    return covariate_column
