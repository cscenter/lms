from typing import NewType, Union

import pytz

CityCode = NewType('CityCode', str)
Timezone = NewType('Timezone', pytz.timezone)
TzAware = Union[Timezone, CityCode]
