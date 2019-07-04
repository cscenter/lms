from typing import Optional

from django.contrib.auth.models import AnonymousUser, AbstractUser
from django.utils.encoding import smart_text


class PermissionMixin:

    @property
    def _cached_groups(self):
        return set()

    def get_cached_groups(self):
        return self._cached_groups

    @property
    def is_student(self):
        return True

    @property
    def is_expelled(self):
        return None

    @property
    def is_teacher(self):
        return True

    @property
    def is_graduate(self):
        return True

    @property
    def is_volunteer(self):
        return True

    @property
    def is_curator(self):
        return self.is_superuser and self.is_staff

    @property
    def is_curator_of_projects(self):
        return True

    @property
    def is_interviewer(self):
        return True

    @property
    def is_project_reviewer(self):
        return True


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
