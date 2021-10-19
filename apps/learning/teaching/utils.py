from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from django.conf import settings

from core.urls import reverse
from courses.models import Course


def get_student_groups_url(course: Course) -> str:
    return reverse('teaching:student_groups:list', kwargs=course.url_kwargs,
                   subdomain=settings.LMS_SUBDOMAIN)


def get_create_student_group_url(course: Course) -> str:
    return reverse('teaching:student_groups:create', kwargs=course.url_kwargs,
                   subdomain=settings.LMS_SUBDOMAIN)


def set_query_parameter(url, param_name, param_value):
    """
    Given a URL, set or replace a query parameter and return the modified URL.
    """
    scheme, netloc, path, query_string, fragment = urlsplit(url)
    query_params = parse_qs(query_string)
    query_params[param_name] = [param_value]
    new_query_string = urlencode(query_params, doseq=True)
    return urlunsplit((scheme, netloc, path, new_query_string, fragment))
