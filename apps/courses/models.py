import datetime
import os.path
from typing import NamedTuple

import pytz
from bitfield import BitField
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Prefetch, Case, When, IntegerField, Value, Count
from django.dispatch import receiver
from django.utils import timezone
from django.utils.encoding import smart_str
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from djchoices import DjangoChoices, C
from model_utils import FieldTracker
from model_utils.models import TimeStampedModel
from sorl.thumbnail import ImageField

from core.mixins import DerivableFieldsMixin
from core.models import LATEX_MARKDOWN_HTML_ENABLED, Location, Branch
from core.timezone import now_local, Timezone, TimezoneAwareModel, \
    TimezoneAwareDateTimeField
from core.urls import reverse, branch_aware_reverse
from core.utils import hashids, get_youtube_video_id, instance_memoize, \
    is_club_site
from courses.constants import ASSIGNMENT_TASK_ATTACHMENT, TeacherRoles, \
    MaterialVisibilityTypes
from courses.utils import get_current_term_pair, get_term_starts_at, \
    TermPair
from files.models import ConfigurableStorageFileField
from files.storage import private_storage
from learning.settings import GradingSystems, ENROLLMENT_DURATION
from .constants import SemesterTypes, ClassTypes
from .managers import CourseTeacherManager, AssignmentManager, \
    CourseClassManager, CourseDefaultManager
from .micawber_providers import get_oembed_html


class LearningSpace(TimezoneAwareModel, models.Model):
    TIMEZONE_AWARE_FIELD_NAME = 'location'

    location = models.ForeignKey(
        Location,
        verbose_name=_("Location|Name"),
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
        help_text=_("Overrides location name"),
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
        return self.name if self.name else str(self.location)

    @property
    def address(self):
        return self.location.address


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
        return "{0} {1}".format(SemesterTypes.values[self.type], self.year)

    def __cmp__(self, other):
        return self.index - other.index

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    @property
    def slug(self):
        return "{0}-{1}".format(self.year, self.type)

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
        self.ends_at = next_term.starts_at(tz) - datetime.timedelta(days=1)
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
    NO_GROUPS = C('no_groups', _('Without Groups'))
    MANUAL = C('manual', _('Manual'))
    BRANCH = C('branch', _('Branch'))


class Course(TimezoneAwareModel, TimeStampedModel, DerivableFieldsMixin):
    TIMEZONE_AWARE_FIELD_NAME = 'main_branch'

    meta_course = models.ForeignKey(
        MetaCourse,
        verbose_name=_("Course"),
        on_delete=models.PROTECT)
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
        help_text=_("LaTeX+Markdown+HTML is enabled; empty description "
                    "will be replaced by course description"),
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
    is_published_in_video = models.BooleanField(
        _("Published in video section"),
        default=False)
    main_branch = models.ForeignKey(Branch,
                                    verbose_name=_("Main Branch"),
                                    related_name="courses",
                                    on_delete=models.PROTECT)
    additional_branches = models.ManyToManyField(
        Branch,
        verbose_name=_("Additional Branches"),
        related_name='additional_branches',
        help_text=_("Branches where the course is also available for "
                    "enrollment"),
        blank=True)
    branches = models.ManyToManyField(
        Branch,
        verbose_name=_("Course Branches"),
        related_name='branches',
        help_text=_("All branches where the course is available for enrollment"),
        through='courses.CourseBranch')
    group_mode = models.CharField(
        verbose_name=_("Student Group Mode"),
        max_length=100,
        choices=StudentGroupTypes.choices,
        default=StudentGroupTypes.BRANCH,
        # Hide this field as implementation detail.
        # Right now we support only `branch` mode.
        editable=False,
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
        max_length=8,
        help_text=_("Default visibility for class materials."),
        choices=MaterialVisibilityTypes.choices,
        default=MaterialVisibilityTypes.VISIBLE)
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
            "course_slug": self.meta_course.slug,
            "semester_year": self.semester.year,
            "semester_type": self.semester.type,
            "branch_code_request": self.main_branch.code
        }

    def get_absolute_url(self, tab=None, **kwargs):
        options = {"subdomain": settings.LMS_SUBDOMAIN, **kwargs}
        if tab is None:
            route_name = 'courses:course_detail'
            url_kwargs = self.url_kwargs
        else:
            route_name = 'courses:course_detail_with_active_tab'
            url_kwargs = {**self.url_kwargs, "tab": tab}
        return branch_aware_reverse(route_name,
                                    kwargs=url_kwargs,
                                    **options)

    def get_url_for_tab(self, active_tab):
        kwargs = {**self.url_kwargs, "tab": active_tab}
        return branch_aware_reverse("courses:course_detail_with_active_tab",
                                    kwargs=kwargs,
                                    subdomain=settings.LMS_SUBDOMAIN)

    def get_create_assignment_url(self):
        return branch_aware_reverse("courses:assignment_add",
                                    kwargs=self.url_kwargs)

    def get_create_news_url(self):
        return branch_aware_reverse("courses:course_news_create",
                                    kwargs=self.url_kwargs)

    def get_create_class_url(self):
        return branch_aware_reverse("courses:course_class_add",
                                    kwargs=self.url_kwargs)

    def get_update_url(self):
        return branch_aware_reverse("courses:course_update",
                                    kwargs=self.url_kwargs)

    def get_enroll_url(self):
        return branch_aware_reverse('course_enroll',
                                    kwargs=self.url_kwargs,
                                    subdomain=settings.LMS_SUBDOMAIN)

    def get_unenroll_url(self):
        return branch_aware_reverse('course_leave',
                                    kwargs=self.url_kwargs,
                                    subdomain=settings.LMS_SUBDOMAIN)

    def get_gradebook_url(self, url_name="teaching:gradebook", format=None):
        if format == "csv":
            url_name = f"{url_name}_csv"
        return branch_aware_reverse(url_name, kwargs=self.url_kwargs)

    def get_course_news_notifications_url(self):
        return branch_aware_reverse('course_news_notifications_read',
                                    kwargs=self.url_kwargs,
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
        from learning.models import EnrollmentPeriod
        # TODO: cache enrollment periods to avoid additional db hits
        enrollment_period = (EnrollmentPeriod.objects
                             .filter(site_id=settings.SITE_ID,
                                     semester=self.semester)
                             .first())
        if not enrollment_period:
            return is_club_site()
        today = now_local(self.get_timezone()).date()
        return today in enrollment_period

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
    def grading_type_choice(self):
        return GradingSystems.get_choice(self.grading_type)

    @instance_memoize
    def is_actual_teacher(self, teacher_id):
        return teacher_id in (co.teacher_id for co in
                              self.course_teachers.all())


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
        _("Notify by default"),
        help_text=(_("Add teacher to assignment notify settings by default")),
        default=False)

    class Meta:
        verbose_name = _("Course Teacher")
        verbose_name_plural = _("Course Teachers")
        unique_together = [['teacher', 'course']]

    objects = CourseTeacherManager()

    def __str__(self):
        return "{0} [{1}]".format(smart_str(self.teacher),
                                  smart_str(self.course_id))

    def get_absolute_url(self, subdomain=settings.LMS_SUBDOMAIN):
        return reverse('teacher_detail', args=[self.teacher_id],
                       subdomain=subdomain)

    def get_abbreviated_name(self, delimiter=chr(160)):  # non-breaking space
        return self.teacher.get_abbreviated_name(delimiter=delimiter)

    @property
    def is_lecturer(self):
        return bool(self.roles.lecturer)

    @classmethod
    def lecturers_prefetch(cls):
        lecturer = cls.roles.lecturer
        return Prefetch(
            'course_teachers',
            queryset=(cls.objects
                      .filter(roles=lecturer)
                      .select_related('teacher')))

    @classmethod
    def get_most_priority_role_prefetch(cls,
                                        lookup='course_teachers') -> Prefetch:
        most_priority_role = cls.get_most_priority_role_expr()
        return Prefetch(
            lookup,
            queryset=(cls.objects
                      .select_related('teacher')
                      .annotate(most_priority_role=most_priority_role)
                      .only('id', 'course_id', 'teacher_id',
                            'teacher__first_name',
                            'teacher__last_name',
                            'teacher__patronymic')
                      .order_by('-most_priority_role',
                                'teacher__last_name',
                                'teacher__first_name')))

    @staticmethod
    def get_most_priority_role_expr():
        """
        Expression for annotating the most priority teacher role.

        It's helpful for showing lecturers first, then seminarians, etc.
        """
        return Case(
            When(roles=CourseTeacher.roles.lecturer, then=Value(8)),
            When(roles=CourseTeacher.roles.seminar, then=Value(4)),
            default=Value(0),
            output_field=IntegerField())

    @staticmethod
    def grouped(course_teachers):
        """
        Group teachers by role.

        A bit complicated to implement this logic on query level without
        ORM hacking.
        """
        # TODO: replace with sql logic after drop sqlite compability at all
        ts = {'lecturers': [], 'others': []}

        def __cmp__(ct):
            return -ct.is_lecturer, ct.teacher.last_name

        for t in sorted(course_teachers, key=__cmp__):
            slot = ts['lecturers'] if t.is_lecturer else ts['others']
            slot.append(t)
        return ts


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


class CourseNews(TimezoneAwareModel, TimeStampedModel):
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
        return branch_aware_reverse('courses:course_news_update', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def get_stats_url(self):
        return reverse('teaching:course_news_unread',
                       kwargs={"news_pk": self.pk})

    def get_delete_url(self):
        return branch_aware_reverse('courses:course_news_delete', kwargs={
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


class CourseClass(TimezoneAwareModel, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'course'  # or venue?

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
        help_text=_("Both YouTube and Yandex Video are supported"))
    other_materials = models.TextField(
        _("CourseClass|Other materials"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    materials_visibility = models.CharField(
        verbose_name=_("Materials Visibility"),
        max_length=8,
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
        super(CourseClass, self).clean()
        # ends_at should be later than starts_at
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            raise ValidationError(_("Class should end after it started"))

    def save(self, *args, **kwargs):
        created = self.pk is None
        if self.slides != self._get_track_field("slides"):
            self.slides_url = ""
        super().save(*args, **kwargs)
        if self.slides and not self.slides_url:
            from .tasks import maybe_upload_slides_yandex
            maybe_upload_slides_yandex.delay(self.pk)
        self._update_track_fields()
        # TODO: make async
        course = Course.objects.get(pk=self.course_id)
        course.compute_fields(
            'youtube_video_id',
            'public_videos_count',
            'public_slides_count',
            'public_attachments_count'
        )

    def get_absolute_url(self):
        return branch_aware_reverse('courses:class_detail', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def get_update_url(self):
        return branch_aware_reverse('courses:course_class_update', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def get_delete_url(self):
        return branch_aware_reverse('courses:course_class_delete', kwargs={
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

    def video_iframe(self):
        return get_oembed_html(self.video_url, 'video_oembed',
                               use_default=True)

    def slides_iframe(self):
        return get_oembed_html(self.slides_url, 'slides_oembed',
                               use_default=False)

    @property
    def slides_file_name(self):
        return os.path.basename(self.slides.name)

    @property
    def materials_is_public(self):
        return self.materials_visibility == MaterialVisibilityTypes.VISIBLE

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


class CourseClassAttachment(TimezoneAwareModel, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'course_class'

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


class AssignmentSubmissionTypes(DjangoChoices):
    ONLINE = C("online", _("Online Submission"))  # file or text on site
    EXTERNAL = C("external", _("External Service"))
    OTHER = C("other", _("No Submission"))  # on paper, etc


class Assignment(TimezoneAwareModel, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'course'

    course = models.ForeignKey(
        Course,
        verbose_name=_("Course offering"),
        on_delete=models.PROTECT)
    deadline_at = TimezoneAwareDateTimeField(_("Assignment|deadline"))
    submission_type = models.CharField(
        verbose_name=_("Submission Type"),
        max_length=42,
        choices=AssignmentSubmissionTypes.choices
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
    notify_teachers = models.ManyToManyField(
        CourseTeacher,
        verbose_name=_("Assignment|notify_settings"),
        help_text=_("Specify who will receive notifications about new comments"),
        blank=True)
    restricted_to = models.ManyToManyField(
        'learning.StudentGroup',
        verbose_name=_("Groups"),
        related_name='restricted_assignments',
        through='learning.AssignmentGroup')

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
            tz = self.get_timezone()
        return timezone.localtime(self.deadline_at, timezone=tz)

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_timezone()
        return timezone.localtime(self.created, timezone=tz)

    def get_teacher_url(self):
        return reverse('teaching:assignment_detail', kwargs={"pk": self.pk})

    def get_update_url(self):
        return branch_aware_reverse('courses:assignment_update', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def get_delete_url(self):
        return branch_aware_reverse('courses:assignment_delete', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def has_unread(self):
        from notifications.middleware import get_unread_notifications_cache
        cache = get_unread_notifications_cache()
        return self.id in cache.assignment_ids_set

    @property
    def deadline_is_exceeded(self):
        return self.deadline_at < timezone.now()

    @property
    def is_online(self):
        """
        Online is when you want students to submit their assignments
        using current site.
        """
        return self.submission_type == AssignmentSubmissionTypes.ONLINE

    @cached_property
    def files_root(self):
        """
        Returns path relative to MEDIA_ROOT.
        """
        bucket = self.course.semester.slug
        return f'assignments/{bucket}/{self.pk}'


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
        max_length=150)

    class Meta:
        ordering = ["assignment", "-created"]
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
        return branch_aware_reverse(
            'courses:assignment_attachment_delete',
            kwargs={
                **self.assignment.course.url_kwargs,
                "assignment_pk": self.assignment.pk,
                "pk": self.pk,
            })
