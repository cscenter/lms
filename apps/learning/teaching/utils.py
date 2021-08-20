from django.conf import settings

from core.urls import reverse
from courses.models import Course


def get_student_groups_url(course: Course) -> str:
    return reverse('teaching:student_groups:list', kwargs=course.url_kwargs,
                   subdomain=settings.LMS_SUBDOMAIN)


def get_create_student_group_url(course: Course) -> str:
    return reverse('teaching:student_groups:create', kwargs=course.url_kwargs,
                   subdomain=settings.LMS_SUBDOMAIN)
