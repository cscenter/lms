import os.path
from datetime import datetime, timedelta
from typing import List, NamedTuple, Optional

import pytz
from bitfield import BitField
from django.contrib.sites.models import Site
from djchoices import C, DjangoChoices
from model_utils import FieldTracker
from model_utils.models import TimeStampedModel
from sorl.thumbnail import ImageField

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Case, Count, F, IntegerField, Q, Value, When
from django.dispatch import receiver
from django.utils import timezone
from django.utils.encoding import smart_str
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from core.db.fields import TimeZoneField
from core.db.mixins import DerivableFieldsMixin
from core.models import LATEX_MARKDOWN_HTML_ENABLED, Branch, Location
from core.timezone import TimezoneAwareMixin, now_local
from core.timezone.fields import TimezoneAwareDateTimeField
from core.timezone.typing import Timezone
from core.urls import reverse
from django.urls import reverse as django_reverse
from core.utils import get_youtube_video_id, hashids, instance_memoize
from courses.constants import (
    AssigneeMode, AssignmentFormat, AssignmentStatus, MaterialVisibilityTypes,
    TeacherRoles
)
from courses.utils import TermPair, get_current_term_pair
from files.models import ConfigurableStorageFileField
from files.storage import private_storage
from learning.settings import GradeTypes, GradingSystems
from learning.utils import humanize_duration

from .constants import ClassTypes, SemesterTypes
from .managers import (
    AssignmentManager, CourseClassManager, CourseDefaultManager, CourseTeacherManager
)


class LearningSpace(TimezoneAwareMixin, models.Model):
    TIMEZONE_AWARE_FIELD_NAME = 'location'

    location = models.ForeignKey(
        Location,
        verbose_name=_("Address"),
        related_name="learning_spaces",
        null=True, blank=True,
        on_delete=models.PROTECT)
    branch = models.ForeignKey(
        Branch,
        verbose_name=_("Branch"),
        related_name="learning_spaces",
        on_delete=models.PROTECT)
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=140,
        help_text=_("The location name will be added to the end if provided"),
        blank=True)
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    order = models.PositiveIntegerField(verbose_name=_('Order'), default=100)

    class Meta:
        verbose_name = _("Learning Space")
        verbose_name_plural = _("Learning Spaces")

    def __str__(self):
        return self.full_name

    @property
    def address(self):
        return self.location.address

    @property
    def full_name(self):
        if self.name:
            return f"{self.name}, {self.location.name}"
        return self.location.name


class Semester(models.Model):
    year = models.PositiveSmallIntegerField(
        _("Year"),
        validators=[MinValueValidator(1990)])
    type = models.CharField(max_length=100,
                            verbose_name=_("Semester|type"),
                            choices=SemesterTypes.choices)
    starts_at = models.DateTimeField(
        verbose_name=_("Semester|StartsAt"),
        help_text=_("Datetime in UTC and is predefined."),
        editable=False)
    ends_at = models.DateTimeField(
        verbose_name=_("Semester|EndsAt"),
        help_text=_("Datetime in UTC and is predefined."),
        editable=False)
    index = models.PositiveSmallIntegerField(
        verbose_name=_("Semester index"),
        help_text=_("System field. Used for sort order and filter."),
        editable=False)

    class Meta:
        ordering = ["-year", "type"]
        verbose_name = _("Semester")
        verbose_name_plural = _("Semesters")
        unique_together = ("year", "type")

    def __str__(self):
        return self.name

    def __cmp__(self, other):
        return self.index - other.index

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    @property
    def slug(self):
        return "{0}-{1}".format(self.year, self.type)

    @property
    def name(self):
        return "{0} {1}".format(SemesterTypes.values[self.type], self.year)

    @property
    def term_pair(self) -> TermPair:
        return TermPair(self.year, self.type)

    @classmethod
    def get_current(cls, tz: Timezone = settings.DEFAULT_TIMEZONE):
        term_pair = get_current_term_pair(tz)
        obj, created = cls.objects.get_or_create(year=term_pair.year,
                                                 type=term_pair.type)
        return obj

    def is_current(self, tz: Timezone = settings.DEFAULT_TIMEZONE):
        term_pair = get_current_term_pair(tz)
        return term_pair.year == self.year and term_pair.type == self.type

    def save(self, *args, **kwargs):
        term_pair = TermPair(self.year, self.type)
        next_term = term_pair.get_next()
        tz = pytz.UTC
        self.index = term_pair.index
        self.starts_at = term_pair.starts_at(tz)
        self.ends_at = next_term.starts_at(tz) - timedelta(days=1)
        super().save(*args, **kwargs)

    @property
    def academic_year(self):
        """
        Academic year runs from September of one year through to late
        August of the following year, with the time split up into three terms.
        """
        if self.type == SemesterTypes.AUTUMN:
            return self.year
        else:
            return self.year - 1


def meta_course_cover_upload_to(instance: "MetaCourse", filename) -> str:
    """
    Generates path to the cover image for the meta course.

    Example:
        meta_courses/data-bases/cover.png
    """
    course_slug = instance.slug
    _, ext = os.path.splitext(filename)
    return os.path.join("meta_courses", course_slug, f"cover{ext}")


class MetaCourse(TimeStampedModel):
    """
    General data shared between all courses of the same type.
    """
    name = models.CharField(_("Course|name"), max_length=140)
    slug = models.SlugField(
        _("News|slug"),
        max_length=70,
        help_text=_("Short dash-separated string "
                    "for human-readable URLs, as in "
                    "test.com/news/<b>some-news</b>/"),
        unique=True)
    description = models.TextField(
        _("Course|description"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    short_description = models.TextField(
        _("Course|short_description"),
        blank=True)
    cover = ImageField(
        _("MetaCourse|cover"),
        upload_to=meta_course_cover_upload_to,
        max_length=200,
        blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Course")
        verbose_name_plural = _("Courses")

    def __str__(self):
        return smart_str(self.name)

    def get_absolute_url(self):
        return reverse('courses:meta_course_detail', kwargs={
            "course_slug": self.slug
        })

    def get_update_url(self):
        return reverse('courses:meta_course_edit', args=[self.slug])

    def get_cover_url(self):
        if self.cover:
            return self.cover.url
        else:
            return staticfiles_storage.url('v2/img/placeholder/meta_course.png')


class StudentGroupTypes(DjangoChoices):
    SYSTEM = C('system', _('System'))
    MANUAL = C('manual', _('Manual'))
    # TODO: protected - manual group with enrollment key
    BRANCH = C('branch', _('Branch'))
    INVITE = C('invite', _('Invitation'))


class CourseGroupModes(DjangoChoices):
    # Enrollment.student_group is nullable, so keep this mode
    # here even if it's not really supported
    NO_GROUPS = C('no_groups', _('No Groups'))
    MANUAL = C('manual', _('Manual'))
    BRANCH = C('branch', _('Branches'))
    INVITE_AND_BRANCH = C('invite_and_branch', _('Invitations and Branches'))


class Course(TimezoneAwareMixin, TimeStampedModel, DerivableFieldsMixin):
    TIMEZONE_AWARE_FIELD_NAME = 'main_branch'

    meta_course = models.ForeignKey(
        MetaCourse,
        verbose_name=_("Course"),
        on_delete=models.PROTECT)
    # TODO: deny update grading system if any final grade exists
    grading_type = models.SmallIntegerField(
        verbose_name=_("CourseOffering|grading_type"),
        choices=GradingSystems.choices,
        default=GradingSystems.BASE)
    capacity = models.PositiveSmallIntegerField(
        verbose_name=_("CourseOffering|capacity"),
        default=0,
        help_text=_("0 - unlimited"))
    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Course|teachers"),
        related_name='teaching_set',
        through='courses.CourseTeacher')
    semester = models.ForeignKey(
        Semester,
        verbose_name=_("Semester"),
        on_delete=models.PROTECT)
    completed_at = models.DateField(
        _("Date of completion"),
        blank=True,
        help_text=_("Consider the course as completed from the specified "
                    "day (inclusive).")
    )
    description = models.TextField(
        _("Description"),
        help_text=_("LaTeX+Markdown+HTML is enabled"),
        blank=True)
    internal_description = models.TextField(
        _("Internal Information"),
        help_text=_("Visible to course listeners only. "
                    "LaTeX+Markdown+HTML is enabled."),
        blank=True)
    contacts = models.TextField(
        _("Contacts"),
        help_text=_("Visible to course listeners only. "
                    "LaTeX+Markdown+HTML is enabled."),
        blank=True)
    survey_url = models.URLField(
        _("Survey URL"),
        blank=True,
        help_text=_("Leave empty if you want to fetch survey url from DB"))
    online_course_url = models.URLField(_("Online Course URL"), blank=True)
    ask_enrollment_reason = models.BooleanField(
        _("Ask Enrollment Reason"),
        help_text=_("Ask a student why they wants to enroll in the course "
                    "when they clicks the 'Enroll' button."),
        default=False)
    ask_ttc = models.BooleanField(
        _("Ask Time to Completion"),
        help_text=_("Teacher must specify estimated amount of time "
                    "required for an assignment to be completed. Student "
                    "enters the actual time on submitting the solution."),
        default=False)
    is_published_in_video = models.BooleanField(
        _("Published in video section"),
        default=False)
    is_visible_in_certificates = models.BooleanField(
        _("Do we see this course in certificates and diplomas?"),
        default=True
    )
    main_branch = models.ForeignKey(Branch,
                                    verbose_name=_("Main Branch"),
                                    related_name="courses",
                                    on_delete=models.PROTECT)
    branches = models.ManyToManyField(
        Branch,
        verbose_name=_("Course Branches"),
        related_name='branches',
        help_text=_("All branches where the course is available for enrollment"),
        through='courses.CourseBranch')
    group_mode = models.CharField(
        verbose_name=_("Student Group Mode"),
        max_length=100,
        choices=CourseGroupModes.choices,
        default=CourseGroupModes.BRANCH,
        help_text=_("Choose `Branch` to auto generate student groups "
                    "from course branches."))
    language = models.CharField(
        verbose_name=_("Language"),
        max_length=5, db_index=True,
        help_text=_("The language in which lectures are given."),
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE)
    materials_visibility = models.CharField(
        verbose_name=_("Materials Visibility"),
        max_length=12,
        help_text=_("Default visibility for class materials."),
        choices=MaterialVisibilityTypes.choices,
        default=MaterialVisibilityTypes.COURSE_PARTICIPANTS)
    # TODO: recalculate on deleting course class
    public_videos_count = models.PositiveIntegerField(default=0, editable=False)
    public_slides_count = models.PositiveIntegerField(
        verbose_name=_("Public Slides"),
        default=0,
        editable=False)
    public_attachments_count = models.PositiveIntegerField(
        verbose_name=_("Public Attachments"),
        default=0,
        editable=False)
    # FIXME: wrong place for this
    youtube_video_id = models.CharField(
        max_length=255, editable=False,
        help_text="Helpful for getting thumbnail on /videos/ page",
        blank=True)
    learners_count = models.PositiveIntegerField(editable=False, default=0)

    objects = CourseDefaultManager()

    derivable_fields = [
        'public_videos_count',
        'public_slides_count',
        'public_attachments_count',
        'youtube_video_id',
        'learners_count',
    ]

    class Meta:
        ordering = ["-semester", "meta_course__created"]
        verbose_name = _("Course offering")
        verbose_name_plural = _("Course offerings")
        constraints = [
            models.UniqueConstraint(
                fields=('meta_course', 'semester', 'main_branch'),
                name='unique_course_for_main_branch_in_a_term'
            ),
        ]

    def __str__(self):
        return "{0}, {1}".format(smart_str(self.meta_course),
                                 smart_str(self.semester))

    def _compute_youtube_video_id(self):
        youtube_video_id = ''
        for course_class in self.courseclass_set.order_by('pk').all():
            if course_class.video_url:
                video_id = get_youtube_video_id(course_class.video_url)
                if video_id is not None:
                    youtube_video_id = video_id
                    break

        if self.youtube_video_id != youtube_video_id:
            self.youtube_video_id = youtube_video_id
            return True

        return False

    def _compute_public_videos_count(self):
        qs = (CourseClass.objects
              .filter(course_id=self.pk)
              .with_public_materials()
              .exclude(video_url=''))
        public_videos_count = qs.count()

        if self.public_videos_count != public_videos_count:
            self.public_videos_count = public_videos_count
            return True

        return False

    def _compute_public_slides_count(self):
        qs = (CourseClass.objects
              .filter(course_id=self.pk)
              .with_public_materials()
              .exclude(slides=''))
        public_slides_count = qs.count()

        if self.public_slides_count != public_slides_count:
            self.public_slides_count = public_slides_count
            return True

        return False

    def _compute_public_attachments_count(self):
        qs = (CourseClass.objects
              .filter(course_id=self.pk)
              .with_public_materials()
              .aggregate(total_attachments=Count('courseclassattachment')))
        public_attachments_count = qs['total_attachments']

        if self.public_attachments_count != public_attachments_count:
            self.public_attachments_count = public_attachments_count
            return True

        return False

    def _compute_learners_count(self):
        """
        Calculate this value with external signal on adding new learner.
        """
        return False

    def save(self, *args, **kwargs):
        # Make sure `self.completed_at` always has value
        if self.semester_id and not self.completed_at:
            term_pair = TermPair(self.semester.year, self.semester.type)
            next_term = term_pair.get_next()
            self.completed_at = next_term.starts_at(self.get_timezone()).date()
        super().save(*args, **kwargs)

    @property
    def url_kwargs(self) -> dict:
        """
        Keyword arguments for the `courses.urls.RE_COURSE_URI` pattern.
        """
        return {
            "course_id": self.pk,
            "course_slug": self.meta_course.slug,
            "main_branch_id": self.main_branch.pk,
            "semester_year": self.semester.year,
            "semester_type": self.semester.type,
        }

    def get_absolute_url(self, tab=None, **kwargs):
        options = {"subdomain": settings.LMS_SUBDOMAIN, **kwargs}
        if tab is None:
            route_name = 'courses:course_detail'
            url_kwargs = self.url_kwargs
        else:
            route_name = 'courses:course_detail_with_active_tab'
            url_kwargs = {**self.url_kwargs, "tab": tab}
        return reverse(route_name, kwargs=url_kwargs, **options)

    def build_absolute_uri(self, site: Optional[Site] = None, is_secure: bool = True):
        # TODO: this is hotfix!!! IDK why it returns absolute url
        url_absolute = reverse('courses:course_detail', kwargs=self.url_kwargs)
        relative_start = url_absolute.find('/courses')
        url = url_absolute[relative_start:]
        scheme = f"http{'s' if is_secure else ''}://"
        if not isinstance(site, Site):
            site = self.main_branch.site
        lms_domain = site.site_configuration.lms_domain
        if not isinstance(lms_domain, str):
            lms_domain = self.main_branch.site.domain
        return scheme + lms_domain + url

    def get_url_for_tab(self, active_tab):
        kwargs = {**self.url_kwargs, "tab": active_tab}
        return reverse("courses:course_detail_with_active_tab", kwargs=kwargs)

    def get_create_assignment_url(self):
        return reverse("courses:assignment_add", kwargs=self.url_kwargs)

    def get_create_news_url(self):
        return reverse("courses:course_news_create", kwargs=self.url_kwargs)

    def get_create_class_url(self):
        return reverse("courses:course_class_add", kwargs=self.url_kwargs)

    def get_update_url(self):
        return reverse("courses:course_update", kwargs=self.url_kwargs)

    def get_enroll_url(self):
        return reverse('course_enroll', kwargs=self.url_kwargs,
                       subdomain=settings.LMS_SUBDOMAIN)

    def get_unenroll_url(self):
        return reverse('course_leave', kwargs=self.url_kwargs,
                       subdomain=settings.LMS_SUBDOMAIN)

    def get_gradebook_url(self, url_name: str = "teaching:gradebook",
                                format: Optional[str] = None,
                                student_group: Optional[int] = None):
        if format == "csv":
            url_name = f"{url_name}_csv"
        url = reverse(url_name, kwargs=self.url_kwargs)
        if student_group is not None:
            url += f'?student_group={student_group}'
        return url

    def get_course_news_notifications_url(self):
        return reverse('course_news_notifications_read', kwargs=self.url_kwargs,
                       subdomain=settings.LMS_SUBDOMAIN)

    def has_unread(self):
        from notifications.middleware import get_unread_notifications_cache
        cache = get_unread_notifications_cache()
        return self in cache.courseoffering_news

    @property
    def name(self):
        return self.meta_course.name

    @property
    def is_club_course(self):
        return self.main_branch.site_id == settings.CLUB_SITE_ID

    @property
    def is_completed(self):
        return self.completed_at <= now_local(self.get_timezone()).date()

    @property
    def in_current_term(self):
        current_term_index = get_current_term_pair(self.get_timezone()).index
        return self.semester.index == current_term_index

    @property
    def enrollment_is_open(self):
        if self.is_completed:
            return False
        enrollment_periods = [e for e in
                              self.semester.enrollmentperiod_set.all()
                              if e.site_id == settings.SITE_ID]
        if not enrollment_periods:
            return False
        today = now_local(self.get_timezone()).date()
        return today in enrollment_periods[0]

    @property
    def is_capacity_limited(self):
        return self.capacity > 0

    @property
    def places_left(self):
        if self.is_capacity_limited:
            return max(0, self.capacity - self.learners_count)
        else:
            return float("inf")

    @property
    def grading_system(self):
        return GradingSystems.get_choice(self.grading_type)

    @property
    def grade_choices(self):
        return GradeTypes.get_choices_for_grading_system(self.grading_type)

    @instance_memoize
    def is_actual_teacher(self, teacher_id):
        for ct in self.course_teachers.all():
            if ct.teacher.id == teacher_id:
                return not bool(ct.roles.spectator)
        return False


class CourseBranch(models.Model):
    branch = models.ForeignKey(
        Branch,
        verbose_name=_("Branch"),
        on_delete=models.CASCADE)
    course = models.ForeignKey(
        Course,
        verbose_name=_("Course"),
        on_delete=models.CASCADE)
    is_main = models.BooleanField(
        verbose_name=_("Main Branch"),
        default=False)

    class Meta:
        verbose_name = _("Course Branch")
        verbose_name_plural = _("Course Branches")
        constraints = [
            models.UniqueConstraint(fields=('course', 'branch'),
                                    name='unique_course_branch'),
        ]

    def save(self, *args, **kwargs):
        created = self.pk is None
        is_main_branch = (self.branch_id == self.course.main_branch_id)
        if self.is_main and not is_main_branch:
            raise ValidationError("Inconsistent state")
        super().save(*args, **kwargs)

    def clean(self):
        if self.is_main and self.branch_id != self.course.main_branch_id:
            raise ValidationError("You can't mark additional branch as main. "
                                  "Don't forget to update or delete the "
                                  "previous record if you change main branch "
                                  "value.")


class CourseTeacher(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE)
    course = models.ForeignKey(
        Course,
        related_name="course_teachers",
        on_delete=models.CASCADE)
    roles = BitField(flags=TeacherRoles.choices,
                     default=(TeacherRoles.LECTURER,))
    notify_by_default = models.BooleanField(
        _("Notifications"),
        default=True)

    tracker = FieldTracker(fields=['teacher'])

    class Meta:
        verbose_name = _("Course Teacher")
        verbose_name_plural = _("Course Teachers")
        unique_together = [['teacher', 'course']]

    objects = CourseTeacherManager()

    def __str__(self):
        return f"{self.teacher}, course: {self.course_id}"

    def get_absolute_url(self, subdomain=settings.LMS_SUBDOMAIN):
        return reverse('teacher_detail', args=[self.teacher_id],
                       subdomain=subdomain)

    def get_abbreviated_name(self, delimiter=chr(160)):  # non-breaking space
        return self.teacher.get_abbreviated_name(delimiter=delimiter)

    @property
    def is_lecturer(self):
        return bool(self.roles.lecturer)

    @staticmethod
    def get_most_priority_role_expr():
        """
        Expression for annotating the most priority teacher role.

        It's helpful for showing lecturers first, then seminarians, etc.
        """
        return Case(
            When(roles=CourseTeacher.roles.spectator, then=Value(-1)),
            When(roles=CourseTeacher.roles.organizer, then=Value(12)),
            When(roles=CourseTeacher.roles.lecturer, then=Value(8)),
            When(roles=CourseTeacher.roles.seminar, then=Value(4)),
            default=Value(0),
            output_field=IntegerField())

    # TODO: rewrite as a generic function with bitwise operations and move to core.utils
    @classmethod
    def has_any_hidden_role(cls, lookup='roles', hidden_roles: Optional[tuple] = None) -> Q:
        """Filter users with given hidden_roles from queryset.
        If hidden_roles is not passed then hides spectator and organizer"""
        assert lookup.endswith('roles')
        if hidden_roles is None:
            hidden_roles = (cls.roles.spectator, cls.roles.organizer)
        mask = 0
        for hidden_role in hidden_roles:
            mask |= hidden_role
        assert mask > 0
        # One of: `field & mask > 0` or `field + field & mask > field`
        return Q(**{f"{lookup}__lt": F(lookup) + F(lookup).bitand(mask)})


class CourseReview(TimeStampedModel):
    course = models.ForeignKey(
        Course,
        related_name="reviews",
        on_delete=models.CASCADE)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Author"),
        blank=True, null=True,
        on_delete=models.CASCADE)
    text = models.TextField(
        verbose_name=_("CourseReview|text"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('course', 'author'),
                                    name='one_author_review_per_course'),
        ]
        verbose_name = _("Course Review")
        verbose_name_plural = _("Course Reviews")

    def __str__(self):
        return f"{self.course} [{self.pk}]"


class CourseNews(TimezoneAwareMixin, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'course'

    course = models.ForeignKey(
        Course,
        verbose_name=_("Course"),
        on_delete=models.PROTECT)
    title = models.CharField(_("CourseNews|title"), max_length=140)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Author"),
        on_delete=models.PROTECT)
    text = models.TextField(
        _("CourseNews|text"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Course news-singular")
        verbose_name_plural = _("Course news-plural")

    def __str__(self):
        return "{0} ({1})".format(smart_str(self.title),
                                  smart_str(self.course))

    def get_update_url(self):
        return reverse('courses:course_news_update', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def get_stats_url(self):
        return reverse('teaching:course_news_unread',
                       kwargs={"news_pk": self.pk})

    def get_delete_url(self):
        return reverse('courses:course_news_delete', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_timezone()
        return timezone.localtime(self.created, timezone=tz)


def course_class_slides_upload_to(instance: "CourseClass", filename) -> str:
    """
    Generates path to uploaded slides. Filename could have collisions if
    more than one class of the same type in a day.

    Format:
        courses/<term_slug>/<branch_code>-<course_slug>/slides/<generated_filename>

    Example:
        courses/2018-autumn/spb-data-bases/slides/data_bases_lecture_231217.pdf
    """
    course = instance.course
    course_slug = course.meta_course.slug
    # Generic filename
    class_date = instance.date.strftime("%d%m%y")
    course_prefix = course_slug.replace("-", "_")
    _, ext = os.path.splitext(filename)
    filename = f"{course_prefix}_{instance.type}_{class_date}{ext}".lower()
    return "{}/courses/{}/{}-{}/slides/{}".format(
        course.main_branch.site_id,
        course.semester.slug,
        course.main_branch.code,
        course_slug,
        filename)


class ClassMaterial(NamedTuple):
    type: str
    name: str
    icon_code: str = None  # svg icon code


class CourseClass(TimezoneAwareMixin, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'time_zone'

    course = models.ForeignKey(
        Course,
        verbose_name=_("Course"),
        on_delete=models.PROTECT)
    venue = models.ForeignKey(
        LearningSpace,
        verbose_name=_("CourseClass|Venue"),
        on_delete=models.PROTECT)
    type = models.CharField(
        _("Type"),
        max_length=100,
        choices=ClassTypes.choices)
    date = models.DateField(_("Date"))
    starts_at = models.TimeField(_("Starts at"))
    ends_at = models.TimeField(_("Ends at"))
    time_zone = TimeZoneField(_("Time Zone"))

    name = models.CharField(_("CourseClass|Name"), max_length=255)
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    slides = ConfigurableStorageFileField(
        _("Slides"),
        blank=True,
        max_length=200,
        upload_to=course_class_slides_upload_to,
        storage=private_storage)
    slides_url = models.URLField(_("SlideShare URL"), blank=True)
    video_url = models.URLField(
        verbose_name=_("Video Recording"),
        blank=True,
        help_text=_("Both YouTube and Yandex Video are supported"),
        max_length=512)
    other_materials = models.TextField(
        _("CourseClass|Other materials"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    materials_visibility = models.CharField(
        verbose_name=_("Materials Visibility"),
        max_length=12,
        help_text=_("Slides, attachments and other materials"),
        choices=MaterialVisibilityTypes.choices)
    restricted_to = models.ManyToManyField(
        'learning.StudentGroup',
        verbose_name=_("Groups"),
        related_name='course_classes',
        through='learning.CourseClassGroup')

    class Meta:
        ordering = ["-date", "course", "-starts_at"]
        verbose_name = _("Class")
        verbose_name_plural = _("Classes")

    objects = CourseClassManager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_track_fields()

    def __str__(self):
        return smart_str(self.name)

    def clean(self):
        super().clean()
        # ends_at should be later than starts_at
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            raise ValidationError(_("Class should end after it started"))

    def save(self, *args, **kwargs):
        created = self.pk is None
        if self.slides != self._get_track_field("slides"):
            self.slides_url = ""
        super().save(*args, **kwargs)
        self._update_track_fields()
        # TODO: make async
        course = Course.objects.get(pk=self.course_id)
        course.compute_fields(
            'youtube_video_id',
            'public_videos_count',
            'public_slides_count',
            'public_attachments_count'
        )

    def starts_at_local(self, tz=None) -> datetime:
        """
        Returns aware datetime in *tz* time zone. If *tz* is not specified
        fallback to the course class time zone.

        Note:
            Ambiguous dates will be resolved with `is_dst=False`
        """
        # Make sure dt_naive is not ambiguous
        dt_naive = datetime.combine(self.date, self.starts_at)
        dt_aware: datetime = self.time_zone.localize(dt_naive)
        if tz:
            return dt_aware.astimezone(tz)
        return dt_aware

    def ends_at_local(self, tz=None) -> datetime:
        """
        Returns aware datetime in *tz* time zone. If *tz* is not specified
        fallback to the course class time zone.

        Note:
            Ambiguous dates will be resolved with `is_dst=False`
        """
        # Make sure dt_naive is not ambiguous
        dt_naive = datetime.combine(self.date, self.ends_at)
        dt_aware: datetime = self.time_zone.localize(dt_naive)
        if tz:
            return dt_aware.astimezone(tz)
        return dt_aware

    def get_absolute_url(self):
        return reverse('courses:class_detail', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def get_update_url(self):
        return reverse('courses:course_class_update', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def get_delete_url(self):
        return reverse('courses:course_class_delete', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def get_slides_download_url(self):
        sid = hashids.encode(self.pk)
        return reverse("courses:download_course_class_slides", kwargs={
            "sid": sid,
            "file_name": self.slides_file_name
        })

    @property
    def _track_fields(self):
        # FIXME: What if tracked field is not in a queryset?
        return "slides",

    def _update_track_fields(self):
        for field in self._track_fields:
            setattr(self, '_original_%s' % field, getattr(self, field))

    def _get_track_field(self, field):
        return getattr(self, '_original_{}'.format(field))

    @property
    def slides_file_name(self):
        return os.path.basename(self.slides.name)

    @property
    def materials_is_public(self):
        """Public materials will be visible to all users"""
        return self.materials_visibility == MaterialVisibilityTypes.PUBLIC

    def get_available_materials(self):
        """
        Returns list of the material types available for the course class.
        Store the amount of attachments in a `attachments_count` attribute
        to prevent db hitting.
        """
        materials = []
        if self.slides:
            m = ClassMaterial(type='slides', name=_("slides"),
                              icon_code='slides')
            materials.append(m)
        if self.video_url:
            m = ClassMaterial(type='video', name=_("video"),
                              icon_code='video')
            materials.append(m)
        if hasattr(self, "attachments_count"):
            attachments_count = self.attachments_count
        else:
            attachments_count = self.courseclassattachment_set.count()
        if attachments_count:
            m = ClassMaterial(type='attachments', name=_("files"),
                              icon_code='files')
            materials.append(m)
        if self.other_materials:
            m = ClassMaterial(type='other_materials', name=_("other"))
            materials.append(m)
        return materials


@receiver(models.signals.post_delete, sender=CourseClass)
def course_class_post_delete(sender, instance: CourseClass, *args, **kwargs):
    instance.course.compute_fields(
        'public_videos_count',
        'public_slides_count',
        'public_attachments_count'
    )


def course_class_attachment_upload_to(self: "CourseClassAttachment",
                                      filename) -> str:
    course = self.course_class.course
    return "{}/courses/{}/{}-{}/materials/{}".format(
        course.main_branch.site_id,
        course.semester.slug,
        course.main_branch.code,
        course.meta_course.slug,
        filename.replace(" ", "_"))


class CourseClassAttachment(TimeStampedModel):

    course_class = models.ForeignKey(
        CourseClass,
        verbose_name=_("Class"),
        on_delete=models.CASCADE)
    material = ConfigurableStorageFileField(
        max_length=200,
        upload_to=course_class_attachment_upload_to,
        storage=private_storage)

    class Meta:
        ordering = ["course_class", "-created"]
        verbose_name = _("Class attachment")
        verbose_name_plural = _("Class attachments")

    def __str__(self):
        return "{0}".format(smart_str(self.material_file_name))

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        if created:
            course = self.course_class.course
            course.compute_fields('public_attachments_count')

    def get_download_url(self):
        sid = hashids.encode(self.pk)
        return reverse("courses:download_course_class_attachment", kwargs={
            "sid": sid,
            "file_name": self.material_file_name
        })

    def get_delete_url(self):
        return reverse("courses:course_class_attachment_delete", kwargs={
            "pk": self.pk
        })

    @property
    def material_file_name(self):
        return os.path.basename(self.material.name)


@receiver(models.signals.post_delete, sender=CourseClassAttachment)
def course_class_attachment_post_delete(sender, instance, *args, **kwargs):
    instance.course_class.course.compute_fields(
        'public_attachments_count'
    )


class Assignment(TimezoneAwareMixin, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'time_zone'

    course = models.ForeignKey(
        Course,
        verbose_name=_("Course offering"),
        on_delete=models.PROTECT)
    deadline_at = TimezoneAwareDateTimeField(_("Assignment|deadline"))
    time_zone = TimeZoneField(_("Time Zone"))
    # TODO: rename to .format
    submission_type = models.CharField(
        verbose_name=_("Assignment Format"),
        max_length=42,
        choices=AssignmentFormat.choices
    )
    title = models.CharField(_("Assignment|name"),
                             max_length=140)
    text = models.TextField(_("Assignment|text"),
                            help_text=LATEX_MARKDOWN_HTML_ENABLED)
    passing_score = models.PositiveSmallIntegerField(
        _("Passing score"),
        default=2,
        validators=[MaxValueValidator(1000)])
    maximum_score = models.PositiveSmallIntegerField(
        _("Maximum score"),
        default=5,
        validators=[MaxValueValidator(1000)])
    weight = models.DecimalField(
        _("Assignment Weight"),
        default=1,
        max_digits=3, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(1)])
    ttc = models.DurationField(
        _("Time to Completion"),
        blank=True, null=True,
        help_text=_("Estimated amount of time required for the task to be completed"))
    assignee_mode = models.CharField(
        verbose_name=_("Assignee mode"),
        help_text=_("Automatic assignment mode of a responsible teacher"),
        max_length=12,
        choices=AssigneeMode.choices)
    assignees = models.ManyToManyField(
        CourseTeacher,
        verbose_name=_("Assignment Assignees"),
        help_text=_("Has lower priority than student group assignees"),
        related_name="+",
        blank=True)
    restricted_to = models.ManyToManyField(
        'learning.StudentGroup',
        verbose_name=_("Groups"),
        related_name='restricted_assignments',
        through='learning.AssignmentGroup')
    checker = models.ForeignKey(
        'grading.Checker',
        on_delete=models.CASCADE,
        verbose_name=_("Checking System"),
        blank=True, null=True,
        related_name='+'
    )

    tracker = FieldTracker(fields=['deadline_at'])

    objects = AssignmentManager()

    class Meta:
        ordering = ["created", "course"]
        verbose_name = _("Assignment")
        verbose_name_plural = _("Assignments")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.pk:
            self._original_course_id = self.course_id

    def clean(self):
        if self.pk and self._original_course_id != self.course_id:
            raise ValidationError(_("Course modification is not allowed"))
        if self.passing_score > self.maximum_score:
            raise ValidationError(_("Passing score should be less than "
                                    "(or equal to) maximum one"))

    def __str__(self):
        return "{0} ({1})".format(smart_str(self.title),
                                  smart_str(self.course))

    def deadline_at_local(self, tz=None):
        if not tz:
            tz = self.time_zone
        return timezone.localtime(self.deadline_at, timezone=tz)

    def created_local(self, tz=None):
        if not tz:
            tz = self.time_zone
        return timezone.localtime(self.created, timezone=tz)

    def get_teacher_url(self):
        return reverse('teaching:assignment_detail', kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse('courses:assignment_update', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def get_delete_url(self):
        return reverse('courses:assignment_delete', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def has_unread(self):
        from notifications.middleware import get_unread_notifications_cache
        cache = get_unread_notifications_cache()
        return self.id in cache.assignment_ids_set

    @property
    def format(self):
        return self.submission_type

    @property
    def deadline_is_exceeded(self):
        return self.deadline_at < timezone.now()

    @cached_property
    def statuses(self) -> List[AssignmentStatus]:
        statuses = [
            AssignmentStatus.NOT_SUBMITTED,
            AssignmentStatus.ON_CHECKING,
            AssignmentStatus.COMPLETED
        ]
        # Only assignments that can be submitted via LMS can have the status NEED_FIXES
        if self.submission_type in [AssignmentFormat.ONLINE, AssignmentFormat.CODE_REVIEW]:
            statuses.append(AssignmentStatus.NEED_FIXES)
        return statuses

    @property
    def is_online(self):
        """
        Online is when you want students to submit their assignments
        using current site.
        """
        return self.submission_type == AssignmentFormat.ONLINE

    @cached_property
    def files_root(self):
        """
        Returns path relative to MEDIA_ROOT.
        """
        bucket = self.course.semester.slug
        return f'assignments/{bucket}/{self.pk}'

    def get_ttc_display(self) -> str:
        if self.ttc is None:
            return "—"
        return humanize_duration(self.ttc)


def assignment_attachment_upload_to(self: "AssignmentAttachment", filename):
    return "{}/assignments/{}/{}/attachments/{}".format(
        self.assignment.course.main_branch.site_id,
        self.assignment.course.semester.slug,
        self.assignment_id,
        filename)


class AssignmentAttachment(TimeStampedModel):
    assignment = models.ForeignKey(
        Assignment,
        verbose_name=_("Assignment"),
        on_delete=models.CASCADE)
    attachment = ConfigurableStorageFileField(
        upload_to=assignment_attachment_upload_to,
        storage=private_storage,
        max_length=200)

    class Meta:
        verbose_name = _("Assignment attachment")
        verbose_name_plural = _("Assignment attachments")

    def __str__(self):
        return "{0}".format(smart_str(self.file_name))

    @property
    def file_name(self):
        return os.path.basename(self.attachment.name)

    @property
    def file_ext(self):
        _, ext = os.path.splitext(self.attachment.name)
        return ext

    def get_download_url(self):
        sid = hashids.encode(self.pk)
        return reverse("study:download_assignment_attachment",
                       kwargs={"sid": sid, "file_name": self.file_name})

    def get_delete_url(self):
        return reverse(
            'courses:assignment_attachment_delete',
            kwargs={
                **self.assignment.course.url_kwargs,
                "assignment_pk": self.assignment.pk,
                "pk": self.pk,
            })
