"""
measurements		ccov_df
---------------------------------------------------

sex 

1,2,3	         	1,2
1,2,3			3
1,2			1,2
1,2			3
3			1,2
3			3

age

25-44			

25-34
35-44


time

spans of multiple years
span of one year


3, 1994-2011, 0-18
3, 1994-2006, 0-18
3, 1994-1996, 0-18

1, 2004-2004, 25-44
2, 2004-2004, 25-34
2, 2004-2004, 35-44

3, 2013-2015, 0-99

1, 1978-1978, 45-54
2, 1978-1978, 45-54

"""

import pytest

import pandas as pd


@fixture
def measurements_1():
    measurements_1 = pd.DataFrame()
    measurements_1["age_lower"] = [0,0,0,25,25,35,0,45,45]
    measurements_1["age_upper"] = [18,18,18,44,34,44,99,54,54]
    measurements_1["time_lower"] = [1994,1994,1994,2004,2004,2004,2013,1978,1978]
    measurements_1["time_upper"] = [2011,2006,1996,2004,2004,2004,2015,1978,1978] 
    measurements_1["x_sex"] = [3,3,3,1,2,2,3,1,2,3,1,2]    

    return measurements_1


@fixture 
def covariates_1():
    covariates_1 = pd.DataFrame()
    covariates_1["age_lower"] = []
    covariates_1["age_upper"] = []
    covariates_1["time_lower"] = []
    covariates_1["time_upper"] = [] 
    covariates_1["x_sex"] = []    
    covariates_1["value"] = []    
    
    return covariates_1


@fixture 
def covariate_column_1():

    covariate_column_1 = pd.Series([])

    return covariate_column_1

    
def test_assign_interpolated_covariate_values(measurements_1, covariates_1):



def test_compute_covariate_age_interval(covariates_1):



def test_generate_covariate_interpolators(covariates_1):



