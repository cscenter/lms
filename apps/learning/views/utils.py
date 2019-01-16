import logging

from core.timezone import CityCode
from users.utils import get_user_city_code

logger = logging.getLogger(__name__)


def get_student_city_code(request) -> CityCode:
    """
    Returns city code for authenticated student.

    Note: For student is critical to have valid city value in settings.
    """
    city_code = get_user_city_code(request)
    # FIXME: нужна ли эта проверка, если она есть в middleware?
    if city_code is None:
        logger.error("Empty city code for "
                     "student {}".format(request.user.pk))
        raise ValueError("Для вашего профиля не был указан "
                         "город. Обратитесь к куратору.")
    return city_code


def get_teacher_city_code(request) -> CityCode:
    """
    Returns city code for authenticated teacher.

    Since teacher can participate in different cities, we can't be
    100% sure in which one he is located right now.
    Let's get location from user settings. It should be OK in most cases.
    """
    city_code = get_user_city_code(request)
    if city_code is None:
        # Fallback to default timezone
        return request.city_code
    return city_code


