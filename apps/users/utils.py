import logging
from typing import Optional

from djchoices import ChoiceItem

from core.timezone import CityCode
from core.utils import is_club_site
from learning.settings import Branches

logger = logging.getLogger(__name__)


def get_user_city_code(request) -> Optional[CityCode]:
    """Returns city code for authenticated user"""
    if is_club_site():
        # On compsciclub.ru user city always depends on subdomain.
        # e.g. for kzn.compsciclub.ru it's `kzn`
        city_code = request.city_code
    else:
        city_code = getattr(request.user, "city_id", None)
    return city_code if city_code else None


def get_student_city_code(request) -> CityCode:
    """
    Returns city code for the authenticated student.

    Note: For student is critical to have valid city value in settings.
    """
    return get_user_city_code(request)


# FIXME: если юзер берётся из request.user, то для него должно перетираться значение бранчи. МОжно ввести аттрибут _branch_code и его предзаполнять.
# А метод get_user_branch его использовать (перенести его в модель User). settings.GET_BRANCH_FROM_SUBDOMAIN
def get_user_branch(user) -> Optional[ChoiceItem]:
    """Avoids fetching data from DB"""
    if user.branch_id:
        return Branches.get_choice(user.branch_id)
    return None



def get_teacher_city_code(request) -> CityCode:
    """
    Returns city code for the authenticated teacher.

    Since teacher can participate in different cities, we can't be
    100% sure in which one he is located right now.
    Let's get location from user settings. It should be OK in most cases.
    """
    city_code = get_user_city_code(request)
    if city_code is None:
        # Fallback to the default timezone
        return request.city_code
    return city_code
