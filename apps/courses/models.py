import datetime
import os.path
from typing import Dict, List

import pytz
from bitfield import BitField
from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.encoding import smart_text
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from model_utils import FieldTracker
from model_utils.models import TimeStampedModel
from sorl.thumbnail import ImageField

from core.mixins import DerivableFieldsMixin
from core.models import LATEX_MARKDOWN_HTML_ENABLED, City, Location, Branch
from core.timezone import now_local, Timezone, TimezoneAwareModel
from core.urls import reverse, branch_aware_reverse
from core.utils import hashids, get_youtube_video_id
from courses.constants import ASSIGNMENT_TASK_ATTACHMENT, TeacherRoles
from courses.utils import get_current_term_pair, get_term_start, \
    next_term_starts_at, get_term_index, get_current_term_index
from learning.settings import GradingSystems, ENROLLMENT_DURATION
from .constants import SemesterTypes, ClassTypes
from .managers import CourseTeacherManager, AssignmentManager, \
    CourseClassManager, CourseDefaultManager
from .micawber_providers import get_oembed_html
from .tasks import maybe_upload_slides_yandex


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
    enrollment_start_at = models.DateField(
        _("Enrollment start at"),
        blank=True,
        null=True,
        help_text=_("Leave blank to fill in with the date of the beginning "
                    "of the term"))
    enrollment_end_at = models.DateField(
        _("Enrollment end at"),
        blank=True,
        null=True,
        help_text=_("Students can enroll on or leave the course "
                    "before this date (inclusive)"))

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

    @classmethod
    def get_current(cls, tz: Timezone = settings.DEFAULT_TIMEZONE):
        year, term_type = get_current_term_pair(tz)
        obj, created = cls.objects.get_or_create(year=year, type=term_type)
        if created:
            obj.save()
        return obj

    def is_current(self, tz: Timezone = settings.DEFAULT_TIMEZONE):
        year, term = get_current_term_pair(tz)
        return year == self.year and term == self.type

    def save(self, *args, **kwargs):
        self.index = get_term_index(self.year, self.type)
        self.starts_at = get_term_start(self.year, self.type, pytz.UTC)
        self.ends_at = next_term_starts_at(self.index) - datetime.timedelta(days=1)
        # Enrollment period starts from the beginning of the term by default
        if not self.enrollment_start_at:
            start_at = get_term_start(self.year, self.type, pytz.UTC).date()
            self.enrollment_start_at = start_at
        if not self.enrollment_end_at:
            lifetime = datetime.timedelta(days=ENROLLMENT_DURATION)
            self.enrollment_end_at = self.enrollment_start_at + lifetime
        super(Semester, self).save(*args, **kwargs)

    def clean(self):
        if self.year and self.type and self.enrollment_end_at:
            start_at = self.enrollment_start_at
            if not start_at:
                start_at = get_term_start(self.year, self.type, pytz.UTC).date()
            if start_at > self.enrollment_end_at:
                if not self.enrollment_start_at:
                    msg = _("Enrollment period end should be later "
                            "than expected term start ({})").format(start_at)
                else:
                    msg = _("Enrollment period end should be later than "
                            "the beginning")
                raise ValidationError(msg)

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
        return smart_text(self.name)

    def get_absolute_url(self):
        return reverse('meta_course_detail', args=[self.slug])

    def get_update_url(self):
        return reverse('meta_course_edit', args=[self.slug])

    def get_cover_url(self):
        if self.cover:
            return self.cover.url
        else:
            return staticfiles_storage.url('v2/img/placeholder/meta_course.png')


class Course(TimezoneAwareModel, TimeStampedModel, DerivableFieldsMixin):
    TIMEZONE_AWARE_FIELD_NAME = 'branch'

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
    is_published_in_video = models.BooleanField(
        _("Published in video section"),
        default=False)
    is_open = models.BooleanField(
        _("Open course offering"),
        help_text=_("This course offering will be available on Computer"
                    "Science Club website so anyone can join"),
        default=False)
    is_correspondence = models.BooleanField(
        _("Correspondence course"),
        default=False)
    city = models.ForeignKey(City, verbose_name=_("City"),
                             default=settings.DEFAULT_CITY_CODE,
                             on_delete=models.PROTECT)
    branch = models.ForeignKey(Branch,
                               verbose_name=_("Branch"),
                               related_name="courses",
                               on_delete=models.PROTECT)
    additional_branches = models.ManyToManyField(
        Branch,
        verbose_name=_("Additional Branches"),
        related_name='additional_branches',
        help_text=_("Branches where the course is also available for "
                    "enrollment"),
        blank=True)
    language = models.CharField(max_length=5, db_index=True,
                                choices=settings.LANGUAGES,
                                default=settings.LANGUAGE_CODE)
    # TODO: recalculate on deleting course class
    videos_count = models.PositiveIntegerField(default=0, editable=False)
    materials_slides = models.BooleanField(default=False, editable=False)
    materials_files = models.BooleanField(default=False, editable=False)
    youtube_video_id = models.CharField(
        max_length=255, editable=False,
        help_text="Helpful for getting thumbnail on /videos/ page",
        blank=True)
    learners_count = models.PositiveIntegerField(editable=False, default=0)

    objects = CourseDefaultManager()

    derivable_fields = [
        'videos_count',
        'youtube_video_id',
        'materials_slides',
        'materials_files',
        'learners_count',
    ]

    prefetch_before_compute_fields = {
        # TODO: remove default ordering for courseclass_set
        'videos_count': ['courseclass_set'],
        'materials_slides': ['courseclass_set']
    }

    class Meta:
        ordering = ["-semester", "meta_course__created"]
        verbose_name = _("Course offering")
        verbose_name_plural = _("Course offerings")
        constraints = [
            models.UniqueConstraint(
                fields=('meta_course', 'semester', 'branch'),
                name='unique_course_for_branch_in_a_term'
            ),
        ]

    def __str__(self):
        return "{0}, {1}".format(smart_text(self.meta_course),
                                 smart_text(self.semester))

    def _compute_videos_count(self):
        videos_count = 0
        for course_class in self.courseclass_set.all():
            if course_class.video_url:
                videos_count += 1

        if self.videos_count != videos_count:
            self.videos_count = videos_count
            return True

        return False

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

    def _compute_materials_slides(self):
        materials_slides = False
        for course_class in self.courseclass_set.all():
            if course_class.slides:
                materials_slides = True
                break

        if self.materials_slides != materials_slides:
            self.materials_slides = materials_slides
            return True

        return False

    def _compute_materials_files(self):
        materials_files = (CourseClassAttachment.objects
                           .filter(course_class__course_id=self.pk)
                           .exists())

        if self.materials_files != materials_files:
            self.materials_files = materials_files
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
            index = get_term_index(self.semester.year, self.semester.type)
            next_term_dt = next_term_starts_at(index, self.get_timezone())
            self.completed_at = next_term_dt.date()
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
            "branch_code_request": self.branch.code
        }

    def get_absolute_url(self, tab=None, **kwargs):
        options = {"subdomain": settings.LMS_SUBDOMAIN, **kwargs}
        if tab is None:
            route_name = 'course_detail'
            url_kwargs = self.url_kwargs
        else:
            route_name = 'course_detail_with_active_tab'
            url_kwargs = {**self.url_kwargs, "tab": tab}
        return branch_aware_reverse(route_name,
                                    kwargs=url_kwargs,
                                    **options)

    def get_url_for_tab(self, active_tab):
        kwargs = {**self.url_kwargs, "tab": active_tab}
        return branch_aware_reverse("course_detail_with_active_tab",
                                    kwargs=kwargs,
                                    subdomain=settings.LMS_SUBDOMAIN)

    def get_create_assignment_url(self):
        return branch_aware_reverse("assignment_add",
                                    kwargs=self.url_kwargs)

    def get_create_news_url(self):
        return branch_aware_reverse("course_news_create",
                                    kwargs=self.url_kwargs)

    def get_create_class_url(self):
        return branch_aware_reverse("course_class_add",
                                    kwargs=self.url_kwargs)

    def get_update_url(self):
        return branch_aware_reverse("course_update",
                                    kwargs=self.url_kwargs)

    def get_enroll_url(self):
        return branch_aware_reverse('course_enroll',
                                    kwargs=self.url_kwargs,
                                    subdomain=settings.LMS_SUBDOMAIN)

    def get_unenroll_url(self):
        return branch_aware_reverse('course_leave',
                                    kwargs=self.url_kwargs,
                                    subdomain=settings.LMS_SUBDOMAIN)

    def get_gradebook_url(self, url_name=None, format=None):
        url_name = url_name or "teaching:gradebook"
        if format == "csv":
            url_name = f"{url_name}_csv"
        return branch_aware_reverse(url_name, kwargs=self.url_kwargs)
    # TODO: Merge with `get_gradebook_url` after migrating to jinja2
    def get_gradebook_csv_url(self):
        return branch_aware_reverse("teaching:gradebook_csv",
                                  kwargs=self.url_kwargs)

    def get_course_news_notifications_url(self):
        return branch_aware_reverse('course_news_notifications_read',
                                    kwargs=self.url_kwargs,
                                    subdomain=settings.LMS_SUBDOMAIN)

    def has_unread(self):
        from notifications.middleware import get_unread_notifications_cache
        cache = get_unread_notifications_cache()
        return self in cache.courseoffering_news

    @property
    def has_classes_with_slides(self):
        return self.materials_slides

    @property
    def has_classes_with_files(self):
        return self.materials_files

    @property
    def is_completed(self):
        return self.completed_at <= now_local(self.get_timezone()).date()

    @property
    def in_current_term(self):
        current_term_index = get_current_term_index(self.get_timezone())
        return self.semester.index == current_term_index

    @property
    def enrollment_is_open(self):
        if self.is_open:
            return True
        if self.is_completed:
            return False
        today = now_local(self.get_timezone()).date()
        start_at = self.semester.enrollment_start_at
        return start_at <= today <= self.semester.enrollment_end_at

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

    def is_actual_teacher(self, teacher):
        return teacher.pk in (co.teacher_id for co in
                              self.course_teachers.all())

    def get_grouped_teachers(self):
        """
        Returns teachers grouped by role.

        A bit complicated to implement this logic on query level without
        ORM hacking.
        """
        # TODO: replace with sql logic after drop sqlite compatibility
        ts = {'lecturers': [], 'others': []}

        def __cmp__(ct):
            return -ct.is_lecturer, ct.teacher.last_name

        for t in sorted(self.course_teachers.all(), key=__cmp__):
            slot = ts['lecturers'] if t.is_lecturer else ts['others']
            slot.append(t)
        return ts


def group_course_teachers(teachers, multiple_roles=False) -> Dict[str, List]:
    """
    Returns teachers grouped by the most priority role for a teacher.
    Groups are also in priority order.

    Set `multiple_roles=True` if you need to take into account
    all teacher roles.
    """
    # Make sure lecturers go first.
    roles_in_priority = [TeacherRoles.LECTURER, TeacherRoles.SEMINAR,
                         *TeacherRoles.values.keys()]
    grouped = {role: [] for role in roles_in_priority}
    for teacher in teachers:
        for role in grouped:
            if role in teacher.roles:
                grouped[role].append(teacher)
                if not multiple_roles:
                    break
    return {k: v for k, v in grouped.items() if v}


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
        return "{0} [{1}]".format(smart_text(self.teacher),
                                  smart_text(self.course_id))

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
        return "{0} ({1})".format(smart_text(self.title),
                                  smart_text(self.course))

    def get_update_url(self):
        return branch_aware_reverse('course_news_update', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def get_stats_url(self):
        return reverse('teaching:course_news_unread',
                       kwargs={"news_pk": self.pk})

    def get_delete_url(self):
        return branch_aware_reverse('course_news_delete', kwargs={
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
    _, ext = os.path.splitext(filename)
    course_prefix = course_slug.replace("-", "_")
    filename = f"{course_prefix}_{instance.type}_{class_date}{ext}".lower()
    return os.path.join("courses", course.semester.slug,
                        f"{course.branch.code}-{course_slug}",
                        "slides", filename)


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
    name = models.CharField(_("CourseClass|Name"), max_length=255)
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    slides = models.FileField(
        _("Slides"),
        blank=True,
        max_length=200,
        upload_to=course_class_slides_upload_to)
    slides_url = models.URLField(_("SlideShare URL"), blank=True)
    video_url = models.URLField(
        _("Video URL"), blank=True,
        help_text=_("Both YouTube and Yandex Video are supported"))
    other_materials = models.TextField(
        _("CourseClass|Other materials"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    date = models.DateField(_("Date"))
    starts_at = models.TimeField(_("Starts at"))
    ends_at = models.TimeField(_("Ends at"))

    class Meta:
        ordering = ["-date", "course", "-starts_at"]
        verbose_name = _("Class")
        verbose_name_plural = _("Classes")

    objects = CourseClassManager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_track_fields()

    def __str__(self):
        return smart_text(self.name)

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
            maybe_upload_slides_yandex.delay(self.pk)
        self._update_track_fields()
        # TODO: make async
        course = Course.objects.get(pk=self.course_id)
        course.compute_fields(
            'videos_count',
            'youtube_video_id',
            'materials_slides',
            'materials_files',
            prefetch=True)

    def get_absolute_url(self):
        return branch_aware_reverse('class_detail', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def get_update_url(self):
        return branch_aware_reverse('course_class_update', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def get_delete_url(self):
        return branch_aware_reverse('course_class_delete', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    @property
    def _track_fields(self):
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


def course_class_attachment_upload_to(instance: "CourseClassAttachment",
                                      filename) -> str:
    """
    Format: courses/<term_slug>/<branch_code>-<course_slug>/materials/<filename>

    Example:
        courses/2018-autumn/spb-data-bases/materials/Лекция_1.pdf
    """
    course = instance.course_class.course
    course_slug = course.meta_course.slug
    filename = filename.replace(" ", "_")
    # TODO: transliterate?
    return os.path.join("courses", course.semester.slug,
                        f"{course.branch.code}-{course_slug}",
                        "materials", filename)


class CourseClassAttachment(TimezoneAwareModel, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'course_class'

    course_class = models.ForeignKey(
        CourseClass,
        verbose_name=_("Class"),
        on_delete=models.CASCADE)
    material = models.FileField(max_length=200,
                                upload_to=course_class_attachment_upload_to)

    class Meta:
        ordering = ["course_class", "-created"]
        verbose_name = _("Class attachment")
        verbose_name_plural = _("Class attachments")

    def __str__(self):
        return "{0}".format(smart_text(self.material_file_name))

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        if created:
            course = self.course_class.course
            course.compute_fields('materials_files')

    def get_delete_url(self):
        return branch_aware_reverse('course_class_attachment_delete', kwargs={
            **self.course_class.course.url_kwargs,
            "class_pk": self.course_class.pk,
            "pk": self.pk
        })

    @property
    def material_file_name(self):
        return os.path.basename(self.material.name)


class Assignment(TimezoneAwareModel, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'course'

    course = models.ForeignKey(
        Course,
        verbose_name=_("Course offering"),
        on_delete=models.PROTECT)
    deadline_at = models.DateTimeField(_("Assignment|deadline"))
    is_online = models.BooleanField(_("Assignment|can be passed online"),
                                    default=True)
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
        _("Problem Weight"),
        default=1,
        max_digits=3, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(1)])
    notify_teachers = models.ManyToManyField(
        CourseTeacher,
        verbose_name=_("Assignment|notify_settings"),
        help_text=_("Leave blank if you want to populate list from "
                    "the course settings"),
        blank=True)

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
        return branch_aware_reverse('assignment_update', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def get_delete_url(self):
        return branch_aware_reverse('assignment_delete', kwargs={
            **self.course.url_kwargs,
            "pk": self.pk
        })

    def clean(self):
        if self.pk and self._original_course_id != self.course_id:
            raise ValidationError(_("Course modification is not allowed"))
        if self.passing_score > self.maximum_score:
            raise ValidationError(_("Passing score should be less than "
                                    "(or equal to) maximum one"))

    def __str__(self):
        return "{0} ({1})".format(smart_text(self.title),
                                  smart_text(self.course))

    def has_unread(self):
        from notifications.middleware import get_unread_notifications_cache
        cache = get_unread_notifications_cache()
        return self.id in cache.assignment_ids_set

    @property
    def is_open(self):
        return self.deadline_at > timezone.now()

    @cached_property
    def files_root(self):
        """
        Returns path relative to MEDIA_ROOT.
        """
        bucket = self.course.semester.slug
        return f'assignments/{bucket}/{self.pk}'


def task_attachment_upload_to(instance: "AssignmentAttachment", filename):
    return f"{instance.assignment.files_root}/attachments/{filename}"


class AssignmentAttachment(TimeStampedModel):
    assignment = models.ForeignKey(
        Assignment,
        verbose_name=_("Assignment"),
        on_delete=models.CASCADE)
    attachment = models.FileField(upload_to=task_attachment_upload_to,
                                  max_length=150)

    class Meta:
        ordering = ["assignment", "-created"]
        verbose_name = _("Assignment attachment")
        verbose_name_plural = _("Assignment attachments")

    def __str__(self):
        return "{0}".format(smart_text(self.file_name))

    @property
    def file_name(self):
        return os.path.basename(self.attachment.name)

    @property
    def file_ext(self):
        _, ext = os.path.splitext(self.attachment.name)
        return ext

    def file_url(self):
        sid = hashids.encode(ASSIGNMENT_TASK_ATTACHMENT, self.pk)
        return reverse("study:assignment_attachments_download",
                       kwargs={"sid": sid, "file_name": self.file_name})

    def get_delete_url(self):
        return branch_aware_reverse('assignment_attachment_delete', kwargs={
            **self.assignment.course.url_kwargs,
            "assignment_pk": self.assignment.pk,
            "pk": self.pk,
        })
