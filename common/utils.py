import datetime
import calendar
from dateutil.relativedelta import relativedelta


def age_to_date(current_age, target_age):
    today = datetime.date.today()
    today = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    year_increment = target_age - current_age
    
    return today + relativedelta(years=year_increment)