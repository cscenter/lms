import logging
import os
import uuid
from random import choice
from string import ascii_lowercase, digits
from typing import List, Optional, Set

from djchoices import C, DjangoChoices
from model_utils import FieldTracker
from model_utils.fields import AutoLastModifiedField, MonitorField
from model_utils.models import TimeStampedModel
from sorl.thumbnail import ImageField
from taggit.models import TagBase

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser, PermissionsMixin, _user_has_perm
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q, prefetch_related_objects
from django.utils import timezone
from django.utils.encoding import force_bytes, smart_str
from django.utils.functional import cached_property
from django.utils.text import normalize_newlines
from django.utils.translation import gettext_lazy as _

from admission.constants import DiplomaDegrees
from api.services import generate_hash
from api.settings import DIGEST_MAX_LENGTH
from auth.permissions import perm_registry
from core.db.fields import TimeZoneField
from core.models import TimestampedModel
from core.timezone import TimezoneAwareMixin
from core.timezone.constants import DATETIME_FORMAT_RU
from core.urls import reverse
from core.utils import (
    instance_memoize, is_club_site, normalize_yandex_login, ru_en_mapping
)
from learning.managers import EnrollmentQuerySet
from learning.settings import AcademicDegreeLevels, GradeTypes, StudentStatuses
from learning.utils import is_negative_grade
from lms.utils import PublicRoute
from notifications.base_models import EmailAddressSuspension
from study_programs.models import StudyProgram, AcademicDiscipline
from users.constants import ConsentTypes, GenderTypes, TShirtSizeTypes
from users.constants import Roles
from users.constants import Roles as UserRoles
from users.constants import SHADCourseGradeTypes
from users.thumbnails import UserThumbnailMixin

from .managers import CustomUserManager

# See 'https://help.yandex.ru/pdd/additional/mailbox-alias.xml'.
YANDEX_DOMAINS = ["yandex.ru", "narod.ru", "yandex.ua",
                  "yandex.by", "yandex.kz", "ya.ru", "yandex.com"]

logger = logging.getLogger(__name__)

# Telegram username may only contain alphanumeric characters or
# single underscores. Should begin only with letter and end with alphanumeric.
TELEGRAM_REGEX = "^(?!.*__.*)[a-z A-Z]\w{3,30}[a-zA-Z0-9]$"
TELEGRAM_USERNAME_VALIDATOR = RegexValidator(regex=TELEGRAM_REGEX)

# Github username may only contain alphanumeric characters or
# single hyphens, and cannot begin or end with a hyphen
GITHUB_LOGIN_VALIDATOR = RegexValidator(regex="^[a-zA-Z0-9](-?[a-zA-Z0-9])*$")


class LearningPermissionsMixin:
    @property
    def site_groups(self):
        return set()

    @property
    def is_curator(self):
        return self.is_superuser and self.is_staff

    @property
    def is_student(self):
        return UserRoles.STUDENT in self.roles

    @property
    def is_volunteer(self):
        return UserRoles.VOLUNTEER in self.roles

    # FIXME: inline
    @property
    def is_active_student(self):
        if is_club_site():
            return self.is_student
        has_perm = self.is_student or self.is_volunteer
        return has_perm and not StudentStatuses.is_inactive(self.status)

    @property
    def is_teacher(self):
        return UserRoles.TEACHER in self.roles

    @property
    def is_graduate(self):
        return UserRoles.GRADUATE in self.roles

    @property
    def is_curator_of_projects(self):
        return UserRoles.CURATOR_PROJECTS in self.roles

    @property
    def is_interviewer(self):
        return UserRoles.INTERVIEWER in self.roles

    @property
    def is_project_reviewer(self):
        return UserRoles.PROJECT_REVIEWER in self.roles

    def get_student_profile(self, site: Site, **kwargs):
        return None


class ExtendedAnonymousUser(LearningPermissionsMixin, AnonymousUser):
    index_redirect = None
    branch_id = None
    roles = set()
    time_zone = None

    def __str__(self):
        return 'ExtendedAnonymousUser'

    def get_enrollment(self, course_id: int) -> Optional["Enrollment"]:
        return None


class Group(models.Model):
    """
    Groups are a generic way of categorizing users to apply some label.
    A user can belong to any number of groups.

    Groups are a convenient way to categorize users to
    apply some label, or extended functionality, to them. For example, you
    could create a group 'Special users', and you could write code that would
    do special things to those users -- such as giving them access to a
    members-only portion of your site, or sending them members-only email
    messages.
    """
    name = models.CharField(_('name'), max_length=150, unique=True)

    class Meta:
        verbose_name = _('group')
        verbose_name_plural = _('groups')

    def __str__(self):
        return self.name

    def natural_key(self):
        return self.name,


def get_current_site():
    return settings.SITE_ID


class UserGroup(models.Model):
    """Maps users to site and groups. Used by users.groups.AccessGroup."""

    user = models.ForeignKey('users.User', verbose_name=_("User"),
                             on_delete=models.CASCADE,
                             related_name="groups",
                             related_query_name="group")
    site = models.ForeignKey('sites.Site', verbose_name=_("Site"),
                             db_index=False,
                             on_delete=models.PROTECT,
                             default=get_current_site)
    branch = models.ForeignKey(
        "core.Branch",
        verbose_name=_("Branch"),
        related_name="+",  # Disable backwards relation
        on_delete=models.PROTECT,
        null=True, blank=True)
    role = models.PositiveSmallIntegerField(_("Role"),
                                            choices=Roles.choices)

    class Meta:
        db_table = "users_user_groups"
        constraints = [
            models.UniqueConstraint(fields=('user', 'role', 'site'),
                                    name='unique_user_role_site'),
        ]
        verbose_name = _("Access Group")
        verbose_name_plural = _("Access Groups")

    @property
    def _key(self):
        """
        Convenience function to make eq overrides easier and clearer.
        Arbitrary decision that group is primary, followed by site and then user
        """
        return self.role, self.site_id, self.user_id

    def __eq__(self, other):
        """
        Overriding eq b/c the django impl relies on the primary key which
        requires fetch. Sometimes we just want to compare groups w/o doing
        another fetch.
        """
        # noinspection PyProtectedMember
        return type(self) == type(other) and self._key == other._key

    def __hash__(self):
        return hash(self._key)

    def __str__(self):
        return "[AccessGroup] user: {}  role: {}  site: {}".format(
            self.user_id, self.role, self.site_id)


class StudentProfileAbstract(models.Model):
    # FIXME: remove
    status = models.CharField(
        choices=StudentStatuses.choices,
        verbose_name=_("Status"),
        max_length=15,
        blank=True)
    index_redirect = models.CharField(
        _("Index Redirect Option"),
        max_length=200,
        choices=PublicRoute.choices(),
        blank=True)

    class Meta:
        abstract = True


def user_photo_upload_to(instance: "User", filename):
    bucket = instance.pk // 1000
    _, ext = os.path.splitext(filename)
    file_name = uuid.uuid4().hex
    return f"profiles/{bucket}/{file_name}{ext}"


class YandexUserData(TimestampedModel):
    """
    This data is obtained from Yandex ID API.
    These constraints obtained experimentally from web-version:
        len(login) = 1..30
        len(display_name) = 1..60
        len(first_name) = 1..50
        len(last_name) = 0..50
        len(real_name) = len(first_name + ' ' + last_name) = 1..101
    ATTENTION:
        yandex login can be blank and in common it's not unique!!!
        Instead, use the UID everywhere.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("User"),
        related_name="yandex_data",
        on_delete=models.CASCADE)
    login = models.CharField(_("Yandex Login"), max_length=64, blank=True)
    uid = models.CharField(_("Yandex UID"), max_length=64, unique=True)

    first_name = models.CharField(_('first name'), max_length=64, blank=True)
    last_name = models.CharField(_('last name'), max_length=64, blank=True)
    display_name = models.CharField(_("Display Name"), max_length=130, blank=True)
    real_name = models.CharField(_("Real name"), max_length=130, blank=True)

    # It can be helpful to determine students with problems in the login field.
    # The login can be generated automatically on the Yandex side so it can be useless.
    # Therefore curators must change the login field manually for the data import to work.
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Changed by"),
        related_name="+",
        null=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = _("Data from Yandex.ID")


class User(TimezoneAwareMixin, LearningPermissionsMixin, StudentProfileAbstract,
           UserThumbnailMixin, EmailAddressSuspension, AbstractBaseUser):
    TIMEZONE_AWARE_FIELD_NAME = "time_zone"

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    GENDER_MALE = GenderTypes.MALE
    GENDER_FEMALE = GenderTypes.FEMALE

    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    patronymic = models.CharField(
        verbose_name=_("CSCUser|patronymic"),
        max_length=100,
        blank=True)
    email = models.EmailField(_('email address'), unique=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    is_superuser = models.BooleanField(
        _('superuser status'),
        default=False,
        help_text=_(
            'Designates that this user has all permissions without '
            'explicitly assigning them.'
        ),
    )

    is_notification_allowed = models.BooleanField(
        _('notification permission status'),
        default=True,
        help_text=_(
            'Designates that this user enabled email notifications '
        ),
    )
    gender = models.CharField(_("Gender"), max_length=1,
                              choices=GenderTypes.choices)
    phone = models.CharField(
        _("Phone"),
        max_length=40,
        blank=True)
    birth_date = models.DateField(_("Date of Birth"), blank=True, null=True)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    modified = AutoLastModifiedField(_('modified'))
    photo = ImageField(
        _("CSCUser|photo"),
        upload_to=user_photo_upload_to,
        blank=True)
    cropbox_data = models.JSONField(
        blank=True,
        null=True
    )
    branch = models.ForeignKey(
        "core.Branch",
        verbose_name=_("Branch"),
        related_name="+",  # Disable backwards relation
        on_delete=models.PROTECT,
        null=True, blank=True)
    time_zone = TimeZoneField(_("Time Zone"), null=True)
    bio = models.TextField(
        _("CSCUser|note"),
        help_text=_("LaTeX+Markdown is enabled"),
        blank=True)
    yandex_login = models.CharField(
        _("Yandex Login"),
        max_length=80,
        blank=True)
    yandex_login_normalized = models.CharField(
        max_length=80,
        editable=False,
        blank=True)
    github_login = models.CharField(
        _("Github Login"),
        max_length=80,
        validators=[GITHUB_LOGIN_VALIDATOR],
        blank=True)
    telegram_username = models.CharField(
        _("Telegram"),
        validators=[TELEGRAM_USERNAME_VALIDATOR],
        max_length=32,
        blank=True)
    codeforces_login = models.CharField(
        _("Codeforces Handle"),
        max_length=80,
        blank=True)
    stepic_id = models.PositiveIntegerField(
        _("stepik.org ID"),
        blank=True,
        null=True)
    anytask_url = models.URLField(_("Anytask URL"), blank=True, null=True)
    social_networks = models.TextField(
        _("Social Networks"),
        help_text=("{}; {}"
                   .format(_("LaTeX+Markdown is enabled"),
                           _("will be shown to curators only"))),
        blank=True,
        null=True)
    private_contacts = models.TextField(
        _("Contact information"),
        help_text=("{}; {}"
                   .format(_("LaTeX+Markdown is enabled"),
                           _("will be shown only to logged-in users"))),
        blank=True)
    workplace = models.CharField(
        _("Workplace"),
        max_length=200,
        blank=True)
    calendar_key = models.CharField(unique=True, max_length=DIGEST_MAX_LENGTH,
                                    blank=True)

    living_place = models.CharField(
        _("Living Place"), max_length=255, null=True, blank=True
    )
    badge_number = models.CharField(
        _("Badge number"), max_length=255, null=True, blank=True
    )

    tshirt_size = models.CharField(_("T-Shirt size"), max_length=4,
                              choices=TShirtSizeTypes.choices, null=True, blank=True)

    objects = CustomUserManager()

    class Meta:
        db_table = 'users_user'
        verbose_name = _("CSCUser|user")
        verbose_name_plural = _("CSCUser|users")

    def get_group_permissions(self, obj=None):
        return PermissionsMixin.get_group_permissions(self, obj)

    def get_all_permissions(self, obj=None):
        return PermissionsMixin.get_all_permissions(self, obj)

    def has_perm(self, perm, obj=None):
        is_registered_permission = perm in perm_registry
        # Superuser implicitly has all permissions added by Django and
        # should have access to the Django admin
        if self.is_active and self.is_superuser and not is_registered_permission:
            return True
        # Otherwise we need to check the backends.
        return _user_has_perm(self, perm, obj)

    def has_perms(self, perm_list, obj=None):
        return PermissionsMixin.has_perms(self, perm_list, obj)

    def has_module_perms(self, app_label):
        return PermissionsMixin.has_module_perms(self, app_label)

    def save(self, **kwargs):
        created = self.pk is None
        self.email = self.__class__.objects.normalize_email(self.email)
        if self.email and not self.yandex_login:
            username, domain = self.email.split("@", 1)
            if domain in YANDEX_DOMAINS:
                self.yandex_login = username
        if self.yandex_login:
            self.yandex_login_normalized = normalize_yandex_login(self.yandex_login)
        if not self.calendar_key:
            self.calendar_key = generate_hash(b'calendar',
                                              force_bytes(self.email))
        if self.yandex_login:
            suffixes = tuple(f"@{d}" for d in YANDEX_DOMAINS)
            if self.yandex_login.endswith(suffixes):
                username, domain = self.yandex_login.rsplit("@", 1)
                self.yandex_login = username

        super().save(**kwargs)

    def add_group(self, role, branch=None, site_id: Optional[int] = None) -> None:
        """Add new role associated with the current site by default"""
        site_id = site_id or settings.SITE_ID
        self.groups.get_or_create(user=self, role=role, branch=branch, site_id=site_id)

    def remove_group(self, role, branch=None, site_id: int = None):
        sid = site_id or settings.SITE_ID
        self.groups.filter(user=self, role=role, branch=branch, site_id=sid).delete()

    @staticmethod
    def generate_random_username(length=30,
                                 chars=ascii_lowercase + digits,
                                 split=4,
                                 delimiter='-',
                                 attempts=10):
        if not attempts:
            return None

        username = ''.join([choice(chars) for _ in range(length)])

        if split:
            username = delimiter.join(
                [username[start:start + split] for start in
                 range(0, len(username), split)])

        try:
            User.objects.get(username=username)
            return User.generate_random_username(
                length=length, chars=chars, split=split, delimiter=delimiter,
                attempts=attempts - 1)
        except User.DoesNotExist:
            return username

    def __str__(self):
        return smart_str(self.get_full_name(True))

    def get_absolute_url(self):
        return reverse('user_detail', args=[self.pk],
                       subdomain=settings.LMS_SUBDOMAIN)

    @instance_memoize
    def get_student_profile(self, site=settings.SITE_ID, **kwargs):
        from users.services import get_student_profile
        return get_student_profile(self, site, **kwargs)

    def get_student_profile_url(self, subdomain=None):
        return reverse('student_profile', args=[self.pk], subdomain=subdomain)

    def get_update_profile_url(self):
        return reverse('user_update', args=[self.pk],
                       subdomain=settings.LMS_SUBDOMAIN)

    def get_classes_icalendar_url(self):
        # Returns relative path
        return reverse('user_ical_classes', args=[self.pk],
                       subdomain=settings.LMS_SUBDOMAIN)

    def get_assignments_icalendar_url(self):
        return reverse('user_ical_assignments', args=[self.pk],
                       subdomain=settings.LMS_SUBDOMAIN)

    # FIXME: remove
    def teacher_profile_url(self, subdomain=settings.LMS_SUBDOMAIN):
        return reverse('teacher_detail', args=[self.pk],
                       subdomain=subdomain)

    def get_full_name(self, last_name_first=False):
        """
        Returns first name, last name and patronymic, with a space in between
        or username if not enough data.

        For bibliographic list use `last_name_first=True`
        """
        if last_name_first:
            parts = (self.last_name, self.first_name, self.patronymic)
        else:
            parts = (self.first_name, self.patronymic, self.last_name)
        full_name = smart_str(" ".join(p for p in parts if p).strip())
        return full_name or self.username

    def get_short_name(self, last_name_first: bool = False) -> str:
        parts = [self.first_name, self.last_name]
        if last_name_first:
            parts.reverse()
        return smart_str(" ".join(parts).strip()) or self.username

    def get_abbreviated_name(self, delimiter=chr(160)):  # non-breaking space
        parts = [self.first_name[:1], self.patronymic[:1], self.last_name]
        name = smart_str(f".{delimiter}".join(p for p in parts if p).strip())
        return name or self.username

    def get_abbreviated_short_name(self, last_name_first=True):
        first_letter = self.first_name[:1] + "." if self.first_name else ""
        if last_name_first:
            parts = [self.last_name, first_letter]
        else:
            parts = [first_letter, self.last_name]
        non_breaking_space = chr(160)
        return non_breaking_space.join(parts).strip() or self.username

    def get_abbreviated_name_in_latin(self):
        """
        Returns transliterated user surname + rest initials in lower case.
        Fallback to username. Useful for LDAP accounts.

        Жуков Иван Викторович -> zhukov.i.v
        Иванов Кирилл -> ivanov.k
        """
        parts = [self.last_name, self.first_name[:1], self.patronymic[:1]]
        parts = [p.lower() for p in parts if p] or [self.username.lower()]
        # TODO: remove apostrophe
        return ".".join(parts).translate(ru_en_mapping)

    def get_yandex_login(self):
        if hasattr(self, 'yandex_data') and self.yandex_data is not None:
            return normalize_yandex_login(self.yandex_data.login)
        return self.yandex_login_normalized

    @property
    def photo_data(self):
        if self.photo:
            try:
                return {
                    "url": self.photo.url,
                    "width": self.photo.width,
                    "height": self.photo.height,
                    "cropbox": self.cropbox_data
                }
            except (IOError, OSError):
                pass
        return None

    def get_short_bio(self):
        """Returns only the first paragraph from the bio."""
        normalized_bio = normalize_newlines(self.bio)
        lf = normalized_bio.find("\n")
        return self.bio if lf == -1 else normalized_bio[:lf]

    @cached_property
    def site_groups(self) -> set:
        return self.get_site_groups(settings.SITE_ID)

    @instance_memoize
    def get_site_groups(self, site) -> Set[UserGroup]:
        # `self.groups` could omit data if groups were prefetched before
        # with a customized queryset (through Prefetch object)
        prefetch_related_objects([self], 'groups')
        site_id = site.pk if isinstance(site, Site) else site
        return {g for g in self.groups.all() if g.site_id == site_id}

    # FIXME: Sort in priority. Curator role must go before teacher role
    @cached_property
    def roles(self) -> set:
        return {g.role for g in self.site_groups}

    @cached_property
    def has_permission_to_drafts(self) -> bool:
        return self.is_teacher or self.is_curator

    @instance_memoize
    def get_enrollment(self, course_id: int) -> Optional["Enrollment"]:
        """Returns student enrollment if it exists and not soft deleted"""
        from learning.models import Enrollment
        return (Enrollment.active
                .filter(student=self, course_id=course_id)
                .select_related('student_profile')
                .order_by()
                .first())

    def get_redirect_options(self):
        """
        Returns list of website sections available for redirect to current
        authenticated user
        """
        sections = []
        if self.is_project_reviewer or self.is_curator_of_projects:
            sections.append(PublicRoute.PROJECTS.choice)
        if self.is_interviewer:
            sections.append(PublicRoute.ADMISSION.choice)
        if self.is_student or self.is_volunteer:
            sections.append(PublicRoute.LEARNING.choice)
        if self.is_teacher:
            sections.append(PublicRoute.TEACHING.choice)
        if self.is_curator:
            sections.append(PublicRoute.STAFF.choice)
        return sections

    def stats(self, semester, enrollments: Optional[EnrollmentQuerySet] = None):
        """
        Stats for SUCCESSFULLY completed courses and enrollments in
        requested term.
        Additional DB queries may occur:
            * enrollment_set
            * enrollment_set__course (for each enrollment)
            * enrollment_set__course__courseclasses (for each course)
            * onlinecourserecord_set
            * shadcourserecord_set
        """
        center_courses = set()
        club_courses = set()
        club_adjusted = 0
        failed_total = 0
        in_current_term_total = 0  # center, club and shad courses
        in_current_term_courses = set()  # center and club courses
        in_current_term_passed = 0  # Center and club courses
        in_current_term_failed = 0  # Center and club courses
        in_current_term_in_progress = 0  # Center and club courses
        enrollments = enrollments or self.enrollment_set(manager='active').all()
        for e in enrollments:
            in_current_term = e.course.semester_id == semester.pk
            if in_current_term:
                in_current_term_total += 1
                in_current_term_courses.add(e.course.meta_course_id)
            if e.course.is_club_course:
                # FIXME: Something wrong with this approach.
                # FIXME: Look for `classes_total` annotation and fix
                if hasattr(e, "classes_total"):
                    classes_total = e.classes_total
                else:
                    classes_total = (e.course.courseclass_set.count())
                contribution = 0.5 if classes_total < 6 else 1
                if e.grade in GradeTypes.satisfactory_grades:
                    club_courses.add(e.course.meta_course_id)
                    club_adjusted += contribution
                    in_current_term_passed += int(in_current_term)
                elif in_current_term:
                    if is_negative_grade(e.grade):
                        failed_total += 1
                        in_current_term_failed += 1
                    else:
                        in_current_term_in_progress += contribution
                else:
                    failed_total += 1
            else:
                if e.grade in GradeTypes.satisfactory_grades:
                    center_courses.add(e.course.meta_course_id)
                    in_current_term_passed += int(in_current_term)
                elif in_current_term:
                    if is_negative_grade(e.grade):
                        failed_total += 1
                        in_current_term_failed += 1
                    else:
                        in_current_term_in_progress += 1
                else:
                    failed_total += 1
        online_total = len(self.onlinecourserecord_set.all())
        shad_total = 0
        for c in self.shadcourserecord_set.all():
            if c.grade in GradeTypes.satisfactory_grades:
                shad_total += 1
            if c.semester_id == semester.pk:
                in_current_term_total += 1
                if is_negative_grade(c.grade):
                    failed_total += 1
            # `not graded` == failed for passed terms
            elif c.grade not in GradeTypes.satisfactory_grades:
                failed_total += 1

        return {
            "failed": {"total": failed_total},
            # All the time
            "passed": {
                "total": len(center_courses) + online_total + shad_total +
                         len(club_courses),
                "adjusted": len(center_courses) + online_total + shad_total +
                            club_adjusted,
                "center_courses": center_courses,
                "club_courses": club_courses,
                "online_total": online_total,
                "shad_total": shad_total
            },
            # FIXME: collect stats for each term
            "in_term": {
                "total": in_current_term_total,
                "courses": in_current_term_courses,  # center and club courses
                "passed": in_current_term_passed,  # center and club
                "failed": in_current_term_failed,  # center and club
                # FIXME: adusted value, not int
                "in_progress": in_current_term_in_progress,
            }
        }


class StudentTypes(DjangoChoices):
    REGULAR = C('regular', _("Regular Student"))
    VOLUNTEER = C('volunteer', _("Co-worker"))
    INVITED = C('invited', _("Invited Student"))
    PARTNER = C('partner', _("Master's Degree Student"))

    @classmethod
    def from_permission_role(cls, role):
        if role == Roles.STUDENT:
            return cls.REGULAR
        elif role == Roles.PARTNER:
            return cls.PARTNER
        elif role == Roles.VOLUNTEER:
            return cls.VOLUNTEER
        elif role == Roles.INVITED:
            return cls.INVITED

    @classmethod
    def to_permission_role(cls, profile_type):
        if profile_type == cls.REGULAR:
            return Roles.STUDENT
        elif profile_type == cls.VOLUNTEER:
            return Roles.VOLUNTEER
        elif profile_type == cls.INVITED:
            return Roles.INVITED
        elif profile_type == cls.PARTNER:
            return Roles.PARTNER


class PartnerTag(TagBase):
    class Meta:
        verbose_name = _("Partner Tag")
        verbose_name_plural = _("Partner Tags")


class StudentProfile(TimeStampedModel):
    site = models.ForeignKey(Site,
                             verbose_name=_("Site"),
                             on_delete=models.PROTECT,
                             editable=False)
    type = models.CharField(
        verbose_name=_("Type"),
        max_length=10,
        choices=StudentTypes.choices)
    priority = models.PositiveIntegerField(
        verbose_name=_("Priority"),  # among other user profiles on site
        editable=False
    )
    partner = models.ForeignKey(
        PartnerTag,
        verbose_name=_("Magistracy"),
        related_name="student_profiles",
        on_delete=models.PROTECT,
        blank=True, null=True)
    user = models.ForeignKey(
        User,
        verbose_name=_("Student"),
        related_name="student_profiles",
        on_delete=models.PROTECT)
    branch = models.ForeignKey(
        "core.Branch",
        verbose_name=_("Branch"),
        related_name="+",  # Disable backwards relation
        on_delete=models.PROTECT)
    status = models.CharField(
        choices=StudentStatuses.choices,
        verbose_name=_("Status"),
        max_length=15,
        blank=True)
    year_of_admission = models.PositiveSmallIntegerField(
        _("Student|admission year"))
    year_of_curriculum = models.PositiveSmallIntegerField(
        _("CSCUser|Curriculum year"),
        validators=[MinValueValidator(2000)],
        blank=True,
        null=True)
    university = models.CharField(
        _("University"),
        max_length=255,
        blank=True)
    faculty = models.TextField(
        _("Faculty"),
        blank=True,
        null=True
    )
    level_of_education_on_admission = models.CharField(
        _("StudentInfo|University year"),
        choices=AcademicDegreeLevels.choices,
        max_length=12,
        null=True, blank=True)
    level_of_education_on_admission_other = models.CharField(
        _("StudentInfo|University year (other)"),
        max_length=12,
        null=True, blank=True)
    diploma_degree = models.CharField(
        _("Degree of diploma"),
        choices=DiplomaDegrees.choices,
        max_length=30,
        null=True,
        blank=True
    )
    is_official_student = models.BooleanField(
        verbose_name=_("Official Student"),
        help_text=_("Passport, consent for processing personal data, "
                    "diploma (optional)"),
        default=False)
    graduate_without_diploma = models.BooleanField(
        verbose_name=_("Graduate without diploma"),
        default=False)
    graduation_year = models.PositiveSmallIntegerField(
        _("StudentProfile|graduation_year"),
        blank=True,
        null=True)
    is_paid_basis = models.BooleanField(
        verbose_name=_("Paid Basis"),
        default=False)
    new_track = models.BooleanField(
        _("Alternative track"),
        blank=True,
        null=True)
    # Fields required for the issuance of an official diploma
    diploma_number = models.CharField(
        verbose_name=_("Diploma Number"),
        max_length=64,
        help_text=_("Number of higher education diploma"),
        blank=True
    )
    diploma_issued_on = models.DateField(
        verbose_name=_("Diploma Issued on"),
        blank=True, null=True
    )
    diploma_issued_by = models.CharField(
        verbose_name=_("Diploma Issued by"),
        max_length=255,
        blank=True,
    )
    snils = models.CharField(
        verbose_name=_("Student SNILS"),
        max_length=64,
        help_text=_("Individual insurance account number"),
        blank=True
    )
    academic_disciplines = models.ManyToManyField(
        'study_programs.AcademicDiscipline',
        verbose_name=_("Fields of study"),
        blank=True)
    comment = models.TextField(
        _("Comment"),
        blank=True)
    comment_changed_at = MonitorField(
        monitor='comment',
        verbose_name=_("Comment changed"),
        default=None,
        blank=True,
        null=True)
    comment_last_author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Author of last edit"),
        on_delete=models.PROTECT,
        related_name='+',
        blank=True,
        null=True)
    invitation = models.ForeignKey(
        "learning.Invitation",
        verbose_name=_("Invitation"),
        blank=True, null=True,
        related_name="student_profiles",
        on_delete=models.SET_NULL)

    tracker = FieldTracker(fields=['status', 'academic_disciplines'])

    class Meta:
        db_table = 'student_profiles'
        verbose_name = _("Student Profile")
        verbose_name_plural = _("Student Profiles")
        constraints = [
            # e.g. user completed distance branch and continue learning on-campus
            models.UniqueConstraint(
                fields=('user', 'branch', 'year_of_admission'),
                name='unique_regular_student_per_admission_campaign',
                condition=Q(type=StudentTypes.REGULAR))
        ]

    def save(self, **kwargs):
        from users.services import get_student_profile_priority
        created = self.pk is None
        self.site_id = self.branch.site_id
        self.priority = get_student_profile_priority(self)
        self.full_clean()
        update_fields = kwargs.get('update_fields', None)
        if update_fields:
            kwargs['update_fields'] = set(update_fields).union({'priority', 'site_id'})
        super().save(**kwargs)
        if StudentProfile.user.is_cached(self):
            instance_memoize.delete_cache(self.user)

    def clean(self):
        graduate_statuses = {StudentStatuses.GRADUATE, StudentStatuses.WILL_GRADUATE}
        if self.type == StudentTypes.INVITED and self.status in graduate_statuses:
            raise ValidationError(f"Status {self.status} is forbidden for invited students")
        if self.graduate_without_diploma and self.status not in graduate_statuses:
            raise ValidationError(f'Для обозначения студента как выпускника без диплома статус должен быть один из '
                                  f'следующих: {[StudentStatuses.get_choice(value).label for value in graduate_statuses]}')
        if self.graduate_without_diploma and self.graduation_year is None:
            raise ValidationError(f'Для обозначения студента как выпускника без диплома нужно выставить год выпуска '
                                  f'из ВУЗа')
        # TODO: move to the service that creates model object, don't leave non-relational model fields here
        established = self.branch.established
        if self.year_of_admission and self.year_of_admission < established:
            msg = _("Value should be >= {} (year of the branch establishment)").format(established)
            raise ValidationError({"year_of_admission": msg})

    def __str__(self):
        return f"[StudentProfile] id: {self.pk} name: {self.get_full_name()} site: {self.site.domain}"

    def get_full_name(self, last_name_first=False):
        return self.user.get_full_name(last_name_first)

    def get_absolute_url(self, subdomain=None):
        return reverse('user_detail', args=[self.user_id],
                       subdomain=settings.LMS_SUBDOMAIN)

    def get_classes_icalendar_url(self):
        return reverse('user_ical_classes', args=[self.pk],
                       subdomain=settings.LMS_SUBDOMAIN)

    def get_assignments_icalendar_url(self):
        return reverse('user_ical_assignments', args=[self.pk],
                       subdomain=settings.LMS_SUBDOMAIN)

    def get_status_display(self):
        if self.status:
            return StudentStatuses.values[self.status]
        # Empty status means studying in progress
        return _("Studying")

    @cached_property
    def syllabus(self) -> Optional[List[StudyProgram]]:
        # XXX: Logic for `None` must be reimplemented in
        # `users.services.get_student_profiles` method which injects cache
        # into student profile objects.
        if not self.year_of_curriculum or self.type == StudentTypes.INVITED:
            return None
        return list(StudyProgram.objects
                    .select_related("academic_discipline")
                    .prefetch_core_courses_groups()
                    .filter(year=self.year_of_curriculum,
                            branch_id=self.branch_id))

    @property
    def academic_discipline(self) -> AcademicDiscipline:
        return self.academic_disciplines.first()

    @property
    def is_active(self):
        return not StudentStatuses.is_inactive(self.status)

    def get_comment_changed_at_display(self, default=''):
        if self.comment_changed_at:
            return self.comment_changed_at.strftime(DATETIME_FORMAT_RU)
        return default


class StudentFieldLog(TimestampedModel):
    changed_at = models.DateField(
        verbose_name=_("Entry Added"),
        default=timezone.now)
    student_profile = models.ForeignKey(
        StudentProfile,
        verbose_name=_("Student"),
        related_name="%(class)s_related",
        on_delete=models.CASCADE)
    entry_author = models.ForeignKey(
        User,
        verbose_name=_("Author"),
        on_delete=models.CASCADE)
    is_processed = models.BooleanField(
        _('Is processed'),
        default=False,
        help_text=_('Designates whether this Log was processed in document list')
    )
    processed_at = models.DateField(
        verbose_name=_("Processed time"),
        blank=True,
        null=True
    )

    class Meta:
        abstract = True
        verbose_name_plural = _("Student Log")

    def __str__(self):
        return str(self.pk)

    def save(self, **kwargs):
        created = self.pk is None
        if not created and self.tracker.has_changed('is_processed'):
            if self.is_processed:
                self.processed_at = timezone.now()
            else:
                self.processed_at = None
        super().save(**kwargs)


class StudentStatusLog(StudentFieldLog):
    former_status = models.CharField(
        choices=StudentStatuses.choices,
        verbose_name=_("Former status"),
        max_length=15,
        blank=True)
    status = models.CharField(
        choices=StudentStatuses.choices,
        verbose_name=_("Status"),
        max_length=15)

    tracker = FieldTracker()  # Must be in child class https://github.com/jazzband/django-model-utils/issues/57

    class Meta:
        verbose_name_plural = _("Student Status Log")
        ordering = ['-changed_at', '-pk']

    def get_status_display(self):
        if self.status:
            return StudentStatuses.values[self.status]
        # Empty status means studies in progress
        return _("Studying")

    def get_former_status_display(self):
        if self.former_status:
            return StudentStatuses.values[self.former_status]
        # Empty status means studies in progress
        return _("Studying")


class StudentAcademicDisciplineLog(StudentFieldLog):
    former_academic_discipline = models.ForeignKey(
        'study_programs.AcademicDiscipline',
        verbose_name=_("Former field of study"),
        on_delete=models.CASCADE,
        related_name="+",  # Disable backwards relation
        blank=True,
        null=True)
    academic_discipline = models.ForeignKey(
        'study_programs.AcademicDiscipline',
        verbose_name=_("Field of study"),
        on_delete=models.CASCADE,
        related_name="+",  # Disable backwards relation
        blank=True,
        null=True)

    tracker = FieldTracker()  # Must be in child class https://github.com/jazzband/django-model-utils/issues/57

    class Meta:
        verbose_name_plural = _("Student Academic Discipline Log")
        ordering = ['-changed_at', '-pk']


class OnlineCourseRecord(TimeStampedModel):
    student = models.ForeignKey(
        User,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)
    name = models.CharField(_("Course|name"), max_length=255)
    url = models.URLField(_("Online Course URL"), blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Online course record")
        verbose_name_plural = _("Online course records")

    def __str__(self):
        return smart_str(self.name)


class SHADCourseRecord(TimeStampedModel):
    student = models.ForeignKey(
        User,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)
    name = models.CharField(_("Course|name"), max_length=255)
    teachers = models.CharField(_("Teachers"), max_length=255)
    semester = models.ForeignKey(
        'courses.Semester',
        verbose_name=_("Semester"),
        on_delete=models.PROTECT)
    grade = models.CharField(
        max_length=100,
        verbose_name=_("Enrollment|grade"),
        choices=SHADCourseGradeTypes.choices,
        default=SHADCourseGradeTypes.NOT_GRADED)

    class Meta:
        ordering = ["name"]
        verbose_name = _("SHAD course record")
        verbose_name_plural = _("SHAD course records")

    @property
    def grade_display(self):
        return SHADCourseGradeTypes.values[self.grade]

    def __str__(self):
        return smart_str("{} [{}]".format(self.name, self.student_id))


class CertificateOfParticipation(TimeStampedModel):
    signature = models.CharField(_("Reference|signature"), max_length=255)
    note = models.TextField(_("Reference|note"), blank=True)
    student_profile = models.ForeignKey(
        StudentProfile,
        verbose_name=_("Student"),
        on_delete=models.CASCADE,
        related_name="certificates_of_participation")

    class Meta:
        verbose_name = _("Student Reference")
        verbose_name_plural = _("Student References")

    def __str__(self):
        return smart_str(self.student_profile)

    def get_absolute_url(self):
        return reverse('student_reference_detail',
                       subdomain=settings.LMS_SUBDOMAIN,
                       args=[self.student_profile.user_id, self.pk])

    @property
    def total_hours(self) -> int:
        if self.student_profile.year_of_curriculum is None or self.student_profile.academic_discipline is None:
            # Error messages are sent in view
            return -1
        # Total hours of academic discipline changed in 2024
        if self.student_profile.year_of_curriculum >= 2022:
            return self.student_profile.academic_discipline.hours
        elif self.student_profile.academic_discipline.code in ("ds", "ml", "in", "ad"):
            return 576
        elif self.student_profile.academic_discipline.code in ("fast1", "fast2"):
            return 288
        elif self.student_profile.academic_discipline.code == "prod_track":
            return 384
        elif self.student_profile.academic_discipline.code == "algo-syst":
            return 288
        else:
            return self.student_profile.academic_discipline.hours

    @property
    def is_student_male(self) -> bool:
        if not self.student_profile.user.gender:
            return True
        return self.student_profile.user.gender == self.student_profile.user.GENDER_MALE

    def is_learning_completed(self) -> bool:
        return self.student_profile.status in (StudentStatuses.GRADUATE, StudentStatuses.EXPELLED)

class UserConsent(TimeStampedModel):
    user = models.ForeignKey(User,
                             verbose_name=_("User"),
                             on_delete=models.CASCADE,
                             related_name="consents")
    type = models.CharField(verbose_name=_("Consent type"),
                            max_length=100,
                            choices=ConsentTypes.choices)

    class Meta:
        verbose_name = _("User Consent")
        verbose_name_plural = _("User Consents")
        unique_together = ('user', 'type')
