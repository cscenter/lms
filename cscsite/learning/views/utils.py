import logging

from core.utils import is_club_site

logger = logging.getLogger(__name__)


def get_student_city_code(request) -> str:
    """
    Returns city code for authenticated student.

    Note: For student is critical to have valid city value in settings.
    """
    if is_club_site():
        city_code = request.city_code
    else:
        city_code = request.user.city_id
        if not city_code:
            logger.error("Empty city code for "
                         "student {}".format(request.user.pk))
            raise ValueError("Для вашего профиля не был указан "
                             "город. Обратитесь к куратору.")
    return city_code


def get_teacher_city_code(request) -> str:
    """
    Returns city code for authenticated teacher.

    Since teacher can participate in different cities, we can't be
    100% sure in which one he is located right now.
    Let's get location from user settings. It should be OK in most cases.
    """
    city_code = request.user.city_id
    # All club branches in msk timezone. If we forgot to provide city
    # for center teacher, fallback to default timezone.
    if is_club_site() or not city_code:
        city_code = request.city_code
    return city_code
