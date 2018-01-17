import logging
import re
from typing import Optional

from django.contrib import messages

from core.exceptions import Redirect
from core.utils import is_club_site
from learning.models import CourseOffering
from learning.settings import SEMESTER_TYPES
from learning.utils import CityCode, semester_slug_re

logger = logging.getLogger(__name__)


def get_user_city_code(request) -> Optional[CityCode]:
    """Returns city code for authenticated user"""
    if is_club_site():
        # On compsciclub.ru we have no concept of `user city`.
        # For compatibility let student city will be equal to sub domain city.
        # For kzn.compsciclub.ru it will be `kzn` and so on.
        city_code = request.city_code
    else:
        city_code = getattr(request.user, "city_id", None)
    return city_code if city_code else None


def get_student_city_code(request) -> str:
    """
    Returns city code for authenticated student.

    Note: For student is critical to have valid city value in settings.
    """
    city_code = get_user_city_code(request)
    if city_code is None:
        logger.error("Empty city code for "
                     "student {}".format(request.user.pk))
        raise ValueError("Для вашего профиля не был указан "
                         "город. Обратитесь к куратору.")
    return city_code


def get_student_city_code_or_redirect(request):
    """
    City code for CS Center student is mandatory. To avoid UB redirect
    students with broken city setting to main page with alert message.
    """
    try:
        return get_student_city_code(request)
    except ValueError as e:
        messages.error(request, e.args[0])
        raise Redirect(to="/")


def get_teacher_city_code(request) -> str:
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
