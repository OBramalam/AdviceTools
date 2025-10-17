import datetime
import calendar
from dateutil.relativedelta import relativedelta
import re
from typing import Union


def age_to_date(current_age, target_age):
    today = datetime.date.today()
    today = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    year_increment = target_age - current_age
    
    return today + relativedelta(years=year_increment)

def to_annual(amount: float) -> float:
    return amount * 12  # Convert monthly to annual - update when we add more simulation step types.


def year_to_simulation_step(date, start_year) -> int:
    return date.year - start_year


def camel_to_snake(name: str) -> str:
    return "".join(["_" + char.lower() if char.isupper() else char for char in name]).lstrip("_")

def snake_to_camel(name: str) -> str:
    return "".join([char.capitalize() for char in name.split("_")])

def convert_key_to_snake(s: str) -> str:
    if " " in s:
        words = s.split(" ")
        for word in words:
            word.title()
    else:
        words = re.findall(r'[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+', s)
    words = [word.title() for word in words]
    s = "".join(words)
    return camel_to_snake(s)

def convert_json_to_snake(obj: Union[object, dict, list]) -> Union[object, dict, list]:
    if isinstance(obj, dict):
        return {convert_key_to_snake(k): convert_json_to_snake(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_json_to_snake(v) for v in obj]
    else:
        return obj
    
def convert_key_to_camel(s: str) -> str:
    return snake_to_camel(s)

def convert_json_to_camel(obj: Union[object, dict, list]) -> Union[object, dict, list]:
    if isinstance(obj, dict):
        return {convert_key_to_camel(k): convert_json_to_camel(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_json_to_camel(v) for v in obj]
    else:
        return obj