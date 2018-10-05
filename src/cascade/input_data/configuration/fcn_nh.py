from scipy import interpolate
import intervals as I
import pandas as pd

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

    #covariates_m, covariates_f 

    #x = covariates[["age_lower", "age_upper"]].mean(axis=1) / 240
    #y = covariates[["time_lower", "time_upper"]].mean(axis=1)

    #f = interpolate.interp2d(x, y, z)    

    #return pd.Series(covariates.iloc[indices]["mean_value"].values, index=measurements.index)


def generate_covariate_interpolators(covariates)
    """
    Args:

    Returns: 
        Dictionary of interpolators, key = x_sex
    """
    # issue: f = interpolate.interp1d(x, y)

    interpolators = dict()

    both = 0
    male = 0.5
    female = -0.5

    sex_both = set([both])
    sex_mf = set([female, both, male])

    covars_sex = set(covariates["x_sex"].unique())

    if len(covars_sex) and covars_sex.issubset(sex_both):

        interpolator = interpolate.interp2d(
            covariates[["age_lower", "age_upper"]].mean(axis=1),
            covariates[["time_lower", "time_upper"]].mean(axis=1), 
            covariates[["mean_value"]])

        interpolators[female] = interpolator
        interpolators[both] = interpolator
        interpolators[male] = interpolator

    elif covars_sex.issubset(sex_mf) and covars_sex.issuperset(sex_mf):

       covariates_f = covariates[covariates["x_sex"] == female]
       covariates_m = covariates[covariates["x_sex"] == male]
       covariates_both = covariates_f.merge(covariates_m)      

       interpolator_f = interpolate.interp2d(
            covariates_f[["age_lower", "age_upper"]].mean(axis=1),
            covariates_f[["time_lower", "time_upper"]].mean(axis=1), 
            covariates_f[["mean_value"]])

       interpolator_m = interpolate.interp2d(
            covariates_m[["age_lower", "age_upper"]].mean(axis=1),
            covariates_m[["time_lower", "time_upper"]].mean(axis=1), 
            covariates_m[["mean_value"]])

       interpolator_both = interpolate.interp2d(
            covariates_both[["age_lower", "age_upper"]].mean(axis=1),
            covariates_both[["time_lower", "time_upper"]].mean(axis=1), 
            covariates_both[["mean_value"]])

    else:

        raise ValueError(f"set of sexes in covariates is {covars_sex}, 
            expecting {sex_both} or {sex_mf}")

    return interpolators


def assign_interpolated_covariate_value(measurements, covariates):
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

    both = 0
    male = 0.5
    female = -0.5

    interpolators = generate_covariate_interpolators(covariates)    

    covariate_column = compute_interpolated_covariate_values(measurements, interpolators)

    return covariate_column


def compute_covariate_age_interval(covariates):
    """
    Create an interval expressing all the ages in the covariates data frame.
    This allows a check like: 9.5 in age_interval

    Returns:
        Interval of ages in the covariates data frame
    """
    age_interval = I.empty()

    # issue: [5,9], [10,14] or [5,10], [10,15], need the latter
    # may need to add one to age_upper    
    age_groups = set(zip(covariates["age_lower"], covariates["age_upper"]))

    for age in age_groups:
        age_interval = age_interval | I.closed(age[0], age[1]) 
    
    return age_interval


def compute_interpolated_covariate_values(measurements, interpolators)

    measurements_f = measurements[measurements["x_sex"]==female]
    measurements_m = measurements[measurements["x_sex"]==male]
    measurements_both = measurements[measurements["x_sex"]==both]

    index_f = measurements_f.index
    index_m = measurements_m.index
    index_both = measurements_both.index

    covariate_f = interpolators[female](
        measurements_f[["age_lower", "age_upper"]].mean(axis=1),
        measurements_f[["time_lower", "time_upper"]].mean(axis=1),
        measurements_f[["mean_value"]])

    covariate_m = interpolators[male](
        measurements_f[["age_lower", "age_upper"]].mean(axis=1),
        measurements_f[["time_lower", "time_upper"]].mean(axis=1),
        measurements_f[["mean_value"]])

    covariate_both = interpolators[both](
        measurements_both[["age_lower", "age_upper"]].mean(axis=1),
        measurements_both[["time_lower", "time_upper"]].mean(axis=1),
        measurements_both[["mean_value"]])

    # set missings using age_interval
    age_interval = compute_covariate_age_interval(covariates)

    cov_f = covariate_f[0]
    cov_m = covariate_m[0]
    cov_both = covariate_both[0]

    covariate_column = pd.Series(cov_f[0]+cov_m[0]+cov_both[0], 
        index=list(index_f)+list(index_m)+list(index_both))

    return covariate_column
            
    
