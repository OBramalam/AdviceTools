from schemas.base_schemas import Profile


def calculate_risk_indicator(years_to_retirement: int):

    if years_to_retirement < 1:
        return 1
    elif years_to_retirement < 3:
        return 2
    elif years_to_retirement < 5:
        return 3
    elif years_to_retirement < 8:
        return 4
    else:
        return 5