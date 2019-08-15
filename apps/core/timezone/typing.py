import datetime
from typing import NewType, Union

CityCode = NewType('CityCode', str)
Timezone = NewType('Timezone', datetime.tzinfo)
TzAware = Union[Timezone, CityCode]
