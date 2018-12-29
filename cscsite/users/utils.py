from typing import Optional

from core.timezone import CityCode
from core.utils import is_club_site


def get_user_city_code(request) -> Optional[CityCode]:
    """Returns city code for authenticated user"""
    if is_club_site():
        # On compsciclub.ru we have no concept of `user city`.
        # For compatibility student city will be equal to sub domain city.
        # For instance for kzn.compsciclub.ru it's' `kzn`.
        city_code = request.city_code
    else:
        city_code = getattr(request.user, "city_id", None)
    return city_code if city_code else None