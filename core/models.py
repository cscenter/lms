from typing import Optional

from django.contrib.auth.models import AnonymousUser, AbstractUser
from django.utils.encoding import smart_text
from djchoices import DjangoChoices, C
from django.utils.translation import ugettext_lazy as _


class AcademicRoles(DjangoChoices):
    STUDENT_CENTER = C(1, _('Student [CENTER]'))
    TEACHER_CENTER = C(2, _('Teacher [CENTER]'))
    GRADUATE_CENTER = C(3, _('Graduate'))
    VOLUNTEER = C(4, _('Volunteer'))
    STUDENT_CLUB = C(5, _('Student [CLUB]'))
    TEACHER_CLUB = C(6, _('Teacher [CLUB]'))
    INTERVIEWER = C(7, _('Interviewer [Admission]'))
    # Should be always set with one of the student group
    # FIXME: Rename it
    MASTERS_DEGREE = C(8, _('Studying for a master degree'))
    PROJECT_REVIEWER = C(9, _('Project reviewer'))
    CURATOR_PROJECTS = C(10, _('Curator of projects'))


class PermissionMixin:

    @property
    def _cached_groups(self):
        return set()

    def get_cached_groups(self):
        return self._cached_groups

    @property
    def is_student(self):
        student_in_center = AcademicRoles.STUDENT_CENTER in self._cached_groups
        return student_in_center or self.is_volunteer

    @property
    def is_expelled(self):
        return None

    @property
    def is_teacher(self):
        return self.is_teacher_center or self.is_teacher_club

    @property
    def is_teacher_club(self):
        return AcademicRoles.TEACHER_CLUB in self._cached_groups

    @property
    def is_teacher_center(self):
        return AcademicRoles.TEACHER_CENTER in self._cached_groups

    @property
    def is_graduate(self):
        return AcademicRoles.GRADUATE_CENTER in self._cached_groups

    @property
    def is_volunteer(self):
        return AcademicRoles.VOLUNTEER in self._cached_groups

    @property
    def is_curator(self):
        return self.is_superuser and self.is_staff

    @property
    def is_curator_of_projects(self):
        return AcademicRoles.CURATOR_PROJECTS in self._cached_groups

    @property
    def is_interviewer(self):
        return AcademicRoles.INTERVIEWER in self._cached_groups

    @property
    def is_project_reviewer(self):
        return AcademicRoles.PROJECT_REVIEWER in self._cached_groups


class ExtendedAnonymousUser(PermissionMixin, AnonymousUser):
    group = []
    city_code = None
    index_redirect = None

    def __str__(self):
        return 'ExtendedAnonymousUser'

    def get_enrollment(self, course_id: int) -> Optional["Enrollment"]:
        return None


class User(PermissionMixin, AbstractUser):
    def get_thumbnail(self, geometry, use_stub=True, **options):
        class Img(object):
            pass
        im = Img()
        im.url = '/media/pages/index/student.png'
        return im

    def get_absolute_url(self):
        return '/v2/pages/profile/'

    def get_short_name(self):
        return (smart_text(" ".join([self.first_name, self.last_name]).strip())
                or self.username)
