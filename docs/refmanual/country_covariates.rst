Country Covariate Algorithms
-----------------------------
Each of these algorithms returns a column of values for a specific country covariate to be
added to a data frame of measurement values (aka bundle data).  

The measurement data contains fields for age_lower, age_upper, time_lower, time_upper, and sex.

A country covariate value needs to be assigned to each measurement.  There is a challenge in that
the age and time intervals, as well as the sex, don't always match-up exactly. 


Algorithm 1: kdtree based on 3 dimensions - age, time, and sex
------------


Algorithm 2: interpolation grid, by sex, based on age and time dimensions
------------

    Linear interpolation is used to determine a covariate value over an age and time grid 
    specified by the mid-points of the age and time intervals in the covariate data.

    Age and Time Dimensions
    ------------------------

    If the covariate is not a by_age covariate (in which case there is only one "age" in 
    the data, age_group = 22 or age_group = 27) or if the covariate exists for only one year, 
    then a 1d linear interpolation is used over the age or time, whichever of the two has more 
    than one value.  If neither has more than one value, an exception is raised.  

    If the covariate has multiple age_group values and multiple year values, a 2D linear 
    interpolation is used.  

    Sex Dimensions
    ---------------

    If the covariate is not by_sex, then a single interpolator is used for female, male, and 
    both_sexes measurement values.  

    If the covariate is by_sex, then 3 separate interpolators are created - one for females,
    one for males, and the average of the male and female values for both_sexes (the covariate
    data will exist for males and females, but not for both).     

    Age and Time Out of Range
    --------------------------

    If the measurement value has an age interval which does not overlap with the age intervals
    available in the covariate data, the covariate value is assigned missing.  For example, 
    the covariate might apply only to adults, and not to children.  

    If the measurement value has a year which falls outside the covariate interpolation grid,
    an extrapolated value will be assigned.         

    Binary Covariate
    -----------------
   
    No special checks or treatment is currently being made.  This means that a value could be
    returned for the covariate which is not 0 or 1.  The shared.covariate table has a column
    for dichotomous, however, at first glance, it does not seem to be a reliable indicator of
    binary variables.  There are several variables which have the descriptor "binary" in the
    covariate_label column, but also have a dichotomous value of 0.     


Algorithm 3: 
------------

    Possibly modify algorithm 2 to incorporate population weights across ranges.

