import logging
import re

from core.utils import is_club_site
from learning.models import CourseOffering
from learning.settings import SEMESTER_TYPES

logger = logging.getLogger(__name__)


term_types = "|".join(slug for slug, _ in SEMESTER_TYPES)
semester_slug_re = re.compile(r"^(?P<term_year>\d{4})-(?P<term_type>" +
                              term_types + ")$")


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


def get_co_from_query_params(query_params, city_code):
    """
    Returns course offering based on URL-parameters.

    We already parsed `city_code` query-param in middleware and attached it
    to request object, so pass it as parameter.
    """
    match = semester_slug_re.search(query_params.get("semester_slug", ""))
    if not match:
        return None
    term_year, term_type = match.group("term_year"), match.group("term_type")
    course_slug = query_params.get("course_slug", "")
    qs = CourseOffering.objects.in_city(city_code)
    try:
        return qs.get(course__slug=course_slug, semester__year=term_year,
                      semester__type=term_type)
    except qs.model.DoesNotExist:
        return None
