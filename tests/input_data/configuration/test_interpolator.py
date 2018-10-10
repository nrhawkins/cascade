import pytest

import numpy as np
import pandas as pd

from cascade.input_data.configuration.builder import assign_interpolated_covariate_values


@pytest.fixture
def measurements_1():
    measurements_1 = pd.DataFrame()
    measurements_1["age_lower"] = [0, 0, 0, 25, 25, 35, 0, 45, 45]
    measurements_1["age_upper"] = [18, 18, 18, 44, 34, 44, 99, 54, 54]
    measurements_1["time_lower"] = [1994, 1994, 1994, 2004, 2004, 2004, 2013, 1978, 1978]
    measurements_1["time_upper"] = [2011, 2006, 1996, 2004, 2004, 2004, 2015, 1978, 1978]
    measurements_1["x_sex"] = [0, 0, 0, 0.5, -0.5, -0.5, 0, 0.5, -0.5]

    return measurements_1


@pytest.fixture
def measurements_2():
    measurements_2 = pd.DataFrame()
    measurements_2["age_lower"] = [0, 0, 0, 25, 25, 35, 0, 45, 45]
    measurements_2["age_upper"] = [18, 18, 18, 44, 34, 44, 99, 54, 54]
    measurements_2["time_lower"] = [1994, 1994, 1994, 2004, 2004, 2004, 2013, 1978, 1978]
    measurements_2["time_upper"] = [2011, 2006, 1996, 2004, 2004, 2004, 2015, 1978, 1978]
    measurements_2["x_sex"] = [0, 0, 0, 0, 0, 0, 0, 0, 0]

    return measurements_2


@pytest.fixture
def covariates_1():
    covariates_1 = pd.DataFrame()
    covariates_1["age_lower"] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                 0, 0, 0, 0, 0, 0, 0, 0]
    covariates_1["age_upper"] = [125, 125, 125, 125, 125, 125, 125, 125, 125, 125,
                                 125, 125, 125, 125, 125, 125, 125, 125, 125, 125,
                                 125, 125, 125, 125, 125, 125, 125, 125]
    covariates_1["time_lower"] = [1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999,
                                  2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
                                  2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017]
    covariates_1["time_upper"] = [1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999,
                                  2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
                                  2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017]
    covariates_1["x_sex"] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                             0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                             0, 0, 0, 0, 0, 0, 0, 0]
    covariates_1["mean_value"] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                  0, 0, 0, 0, 0, 0, 0, 0]

    return covariates_1


@pytest.fixture
def covariates_2():
    covariates_2 = pd.DataFrame()
    covariates_2["age_lower"] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                 0, 0, 0, 0, 0, 0, 0, 0,
                                 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                 0, 0, 0, 0, 0, 0, 0, 0]
    covariates_2["age_upper"] = [125, 125, 125, 125, 125, 125, 125, 125, 125, 125,
                                 125, 125, 125, 125, 125, 125, 125, 125, 125, 125,
                                 125, 125, 125, 125, 125, 125, 125, 125,
                                 125, 125, 125, 125, 125, 125, 125, 125, 125, 125,
                                 125, 125, 125, 125, 125, 125, 125, 125, 125, 125,
                                 125, 125, 125, 125, 125, 125, 125, 125]
    covariates_2["time_lower"] = [1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999,
                                  2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
                                  2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017,
                                  1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999,
                                  2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
                                  2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017]
    covariates_2["time_upper"] = [1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999,
                                  2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
                                  2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017,
                                  1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999,
                                  2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
                                  2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017]
    covariates_2["x_sex"] = [-0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5,
                             -0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5,
                             -0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5,
                             0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
                             0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
                             0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    covariates_2["mean_value"] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                  0, 0, 0, 0, 0, 0, 0, 0,
                                  2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
                                  2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
                                  2, 2, 2, 2, 2, 2, 2, 2]

    return covariates_2


@pytest.fixture
def covariates_3():
    covariates_3 = pd.DataFrame()
    covariates_3["age_lower"] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                 0, 0, 0, 0, 0, 0, 0, 0,
                                 30, 30, 30, 30, 30, 30, 30, 30, 30, 30,
                                 30, 30, 30, 30, 30, 30, 30, 30, 30, 30,
                                 30, 30, 30, 30, 30, 30, 30, 30]
    covariates_3["age_upper"] = [25, 25, 25, 25, 25, 25, 25, 25, 25, 25,
                                 25, 25, 25, 25, 25, 25, 25, 25, 25, 25,
                                 25, 25, 25, 25, 25, 25, 25, 25,
                                 125, 125, 125, 125, 125, 125, 125, 125, 125, 125,
                                 125, 125, 125, 125, 125, 125, 125, 125, 125, 125,
                                 125, 125, 125, 125, 125, 125, 125, 125]
    covariates_3["time_lower"] = [1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999,
                                  2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
                                  2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017,
                                  1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999,
                                  2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
                                  2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017]
    covariates_3["time_upper"] = [1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999,
                                  2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
                                  2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017,
                                  1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999,
                                  2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009,
                                  2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017]
    covariates_3["x_sex"] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                             0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                             0, 0, 0, 0, 0, 0, 0, 0,
                             0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                             0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                             0, 0, 0, 0, 0, 0, 0, 0]
    covariates_3["mean_value"] = [4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
                                  4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
                                  4, 4, 4, 4, 4, 4, 4, 4,
                                  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                  0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                  0, 0, 0, 0, 0, 0, 0, 0]

    return covariates_3


@pytest.fixture
def covariate_column_1():

    covariate_column_1 = pd.Series([0.0, 0.0, np.nan, 0.0, np.nan, 0.0, 0.0, 0.0, 0.0],
                                   index=[4, 5, 8, 3, 7, 0, 1, 2, 6])

    return covariate_column_1.sort_index()


@pytest.fixture
def covariate_column_2():

    covariate_column_2 = pd.Series([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, np.nan, np.nan],
                                   index=[0, 1, 2, 3, 4, 5, 6, 7, 8])

    return covariate_column_2


@pytest.fixture
def covariate_column_3():

    covariate_column_3 = pd.Series([np.nan, 2.338462, 1.723077, 2.646154,
                                    1.723077, 4.000000, 4.000000, 4.000000,
                                    1.723077],
                                   index=[4, 5, 8, 3, 7, 0, 1, 2, 6])

    return covariate_column_3.sort_index()


def test_assign_interpolated_covariate_values_sex_both_1d(measurements_1, covariates_1, covariate_column_1):

    cov_col = assign_interpolated_covariate_values(measurements_1, covariates_1)

    print(f"cov_col shape: {cov_col.shape}")
    print(f"cov_col: \n{cov_col}")
    print(f"cov_col 1: \n{covariate_column_1}")

    pd.testing.assert_series_equal(covariate_column_1, cov_col)


def test_assign_interpolated_covariate_values_sex_mf_1d(measurements_2, covariates_2, covariate_column_2):

    cov_col = assign_interpolated_covariate_values(measurements_2, covariates_2)

    print(f"cov_col shape: {cov_col.shape}")
    print(f"cov_col: \n{cov_col}")
    print(f"cov col 2: \n{covariate_column_2}")

    pd.testing.assert_series_equal(covariate_column_2, cov_col)


def test_assign_interpolated_covariate_values_sex_both_2d(measurements_1, covariates_3, covariate_column_3):

    cov_col = assign_interpolated_covariate_values(measurements_1, covariates_3)

    print(f"\ncov_col shape: {cov_col.shape}")
    print(f"cov_col: \n{cov_col}")
    print(f"cov col 3: \n{covariate_column_3}")

    pd.testing.assert_series_equal(covariate_column_3, cov_col, check_exact=False)
