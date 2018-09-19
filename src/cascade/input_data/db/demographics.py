from cascade.input_data.db import db_queries

# FIXME: This should come from central comp tools but I don't see a spot...
EPI_AGE_GROUP_SET_ID = 12


def get_age_groups(execution_context):
    groups = db_queries.get_age_metadata(
        age_group_set_id=EPI_AGE_GROUP_SET_ID, gbd_round_id=execution_context.parameters.gbd_round_id
    )
    return groups[["age_group_id", "age_group_years_start", "age_group_years_end"]]


def get_years(execution_context):
    return db_queries.get_demographics(gbd_team="epi", gbd_round_id=execution_context.parameters.gbd_round_id)[
        "year_id"
    ]