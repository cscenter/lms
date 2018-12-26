import datetime
import os.path

import pytz
from bitfield import BitField
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import smart_text
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from model_utils import FieldTracker
from model_utils.models import TimeStampedModel

from core.mixins import DerivableFieldsMixin
from core.models import LATEX_MARKDOWN_HTML_ENABLED, City
from core.timezone import now_local
from core.utils import city_aware_reverse, hashids
from courses.utils import get_current_term_pair, get_term_start, \
    next_term_starts_at, get_term_index, get_current_term_index
from learning.settings import GradingSystems, ENROLLMENT_DURATION, \
    ASSIGNMENT_TASK_ATTACHMENT
from .managers import CourseTeacherManager, AssignmentManager, \
    CourseClassQuerySet, CourseDefaultManager
from .micawber_providers import get_oembed_html
from .settings import SemesterTypes, ClassTypes
from .tasks import maybe_upload_slides_yandex


class Semester(models.Model):
    year = models.PositiveSmallIntegerField(
        _("Year"),
        validators=[MinValueValidator(1990)])
    type = models.CharField(max_length=100,
                            verbose_name=_("Semester|type"),
                            choices=SemesterTypes.choices)
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

    report_starts_at = models.DateField(
        _("Report start"),
        blank=True,
        null=True,
        help_text=_("Start point of project report period."))

    report_ends_at = models.DateField(
        _("Report end"),
        blank=True,
        null=True,
        help_text=_("End point of project report period."))

    # Projects settings.
    # unsatisfactory [PASS BORDER] pass [GOOD BORDER] good [EXCELLENT BORDER]
    projects_grade_excellent = models.SmallIntegerField(
        _("Projects|Border for excellent"),
        blank=True,
        null=True,
        help_text=_("Semester|projects_grade_excellent"))
    projects_grade_good = models.SmallIntegerField(
        _("Projects|Border for good"),
        blank=True,
        null=True,
        help_text=_("Semester|projects_grade_good"))
    projects_grade_pass = models.SmallIntegerField(
        _("Projects|Border for pass"),
        blank=True,
        null=True,
        help_text=_("Semester|projects_grade_pass"))

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

    @cached_property
    def starts_at(self):
        """
        Term start point in datetime format.

        Helps to validate class date range in `CourseClassForm`
        """
        return get_term_start(self.year, self.type, pytz.UTC)

    @cached_property
    def ends_at(self):
        return next_term_starts_at(self.index) - datetime.timedelta(days=1)

    @classmethod
    def get_current(cls):
        # FIXME: Respect timezone. Hard coded city code
        year, term_type = get_current_term_pair('spb')
        obj, created = cls.objects.get_or_create(year=year,
                                                 type=term_type)
        if created:
            obj.save()
        return obj

    def is_current(self):
        # FIXME: Respect timezone. Hard coded city code
        year, term = get_current_term_pair('spb')
        return year == self.year and term == self.type

    def save(self, *args, **kwargs):
        self.index = get_term_index(self.year, self.type)
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

    def get_academic_year(self):
        """Academic year starts from autumn term"""
        if self.type == SemesterTypes.AUTUMN:
            return self.year
        else:
            return self.year - 1


class Venue(models.Model):
    INTERVIEW = 'interview'
    LECTURE = 'lecture'
    UNSPECIFIED = 0  # BitField uses BigIntegerField internal

    city = models.ForeignKey(City, null=True, blank=True,
                             verbose_name=_("City"),
                             default=settings.DEFAULT_CITY_CODE,
                             on_delete=models.PROTECT)
    sites = models.ManyToManyField(Site)
    name = models.CharField(_("Venue|Name"), max_length=140)
    address = models.CharField(
        _("Venue|Address"),
        help_text=(_("Should be resolvable by Google Maps")),
        max_length=500,
        blank=True)
    description = models.TextField(
        _("Description"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    directions = models.TextField(
        _("Directions"),
        blank=True,
        null=True)
    flags = BitField(
        verbose_name=_("Flags"),
        flags=(
            (LECTURE, _('Class')),
            (INTERVIEW, _('Interview')),
        ),
        default=(LECTURE,),
        help_text=(_("Set purpose of this place")))
    is_preferred = models.BooleanField(
        _("Preferred"),
        help_text=(_("Will be displayed on top of the venue list")),
        default=False)

    class Meta:
        ordering = ["-is_preferred", "name"]
        verbose_name = _("Venue")
        verbose_name_plural = _("Venues")

    def get_city_timezone(self):
        return settings.TIME_ZONES[self.city_id]

    @property
    def city_aware_field_name(self):
        return self.__class__.city.field.name

    def __str__(self):
        return "{0}".format(smart_text(self.name))

    def get_absolute_url(self):
        return reverse('venue_detail', args=[self.pk])


class MetaCourse(TimeStampedModel):
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

    class Meta:
        ordering = ["name"]
        verbose_name = _("Course")
        verbose_name_plural = _("Courses")

    def __str__(self):
        return smart_text(self.name)

    def get_absolute_url(self):
        return reverse('meta_course_detail', args=[self.slug])


class Course(TimeStampedModel, DerivableFieldsMixin):
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
    reviews = models.TextField(
        _("Course reviews"),
        null=True,
        blank=True)
    survey_url = models.URLField(_("Survey URL"), blank=True,
                                 help_text=_("Link to Survey"))
    online_course_url = models.URLField(_("Online Course URL"), blank=True)
    is_published_in_video = models.BooleanField(
        _("Published in video section"),
        default=False)
    # Derivable fields depends on course class materials only
    materials_video = models.BooleanField(default=False, editable=False)
    materials_slides = models.BooleanField(default=False, editable=False)
    materials_files = models.BooleanField(default=False, editable=False)

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
    language = models.CharField(max_length=5, db_index=True,
                                choices=settings.LANGUAGES,
                                default=settings.LANGUAGE_CODE)

    objects = CourseDefaultManager()

    derivable_fields = ['materials_video', 'materials_slides', 'materials_files']
    prefetch_before_compute_fields = {
        # TODO: remove default ordering
        'all': ['courseclass_set']
    }

    class Meta:
        ordering = ["-semester", "meta_course__created"]
        verbose_name = _("Course offering")
        verbose_name_plural = _("Course offerings")
        unique_together = [('meta_course', 'semester', 'city')]

    def __str__(self):
        return "{0}, {1}".format(smart_text(self.meta_course),
                                 smart_text(self.semester))

    def _compute_materials_video(self):
        materials_video = False
        for course_class in self.courseclass_set.all():
            if course_class.video_url.strip() != "":
                materials_video = True
                break

        if self.materials_video != materials_video:
            self.materials_video = materials_video
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

    def save(self, *args, **kwargs):
        # Make sure `self.completed_at` always has value
        if self.semester_id and not self.completed_at:
            index = get_term_index(self.semester.year, self.semester.type)
            next_term_dt = next_term_starts_at(index, self.get_city_timezone())
            self.completed_at = next_term_dt.date()
        super().save(*args, **kwargs)

    def _get_url_kwargs(self) -> dict:
        """
        Returns keyword arguments useful for most of course offering url
        patterns.
        """
        return {
            "course_slug": self.meta_course.slug,
            "semester_slug": self.semester.slug,
            "city_code": self.get_city()
        }

    def get_absolute_url(self):
        return city_aware_reverse('course_detail',
                                  kwargs=self._get_url_kwargs())

    def get_url_for_tab(self, active_tab):
        kwargs = {**self._get_url_kwargs(), "tab": active_tab}
        return city_aware_reverse("course_detail_with_active_tab",
                                  kwargs=kwargs)

    def get_create_assignment_url(self):
        return city_aware_reverse("assignment_add",
                                  kwargs=self._get_url_kwargs())

    def get_create_news_url(self):
        return city_aware_reverse("course_news_create",
                                  kwargs=self._get_url_kwargs())

    def get_create_class_url(self):
        return city_aware_reverse("course_class_add",
                                  kwargs=self._get_url_kwargs())

    def get_update_url(self):
        return city_aware_reverse("course_update",
                                  kwargs=self._get_url_kwargs())

    def get_enroll_url(self):
        return city_aware_reverse('course_enroll',
                                  kwargs=self._get_url_kwargs())

    def get_unenroll_url(self):
        return city_aware_reverse('course_leave',
                                  kwargs=self._get_url_kwargs())

    def get_gradebook_url(self, for_curator=False, format=None):
        if for_curator:
            url_name = "staff:course_markssheet_staff"
        elif format == "csv":
            url_name = "gradebook:markssheet_teacher_csv"
        else:
            url_name = "gradebook:markssheet_teacher"
        return reverse(url_name, kwargs={
            "course_slug": self.meta_course.slug,
            "city": self.get_city(),
            "semester_type": self.semester.type,
            "semester_year": self.semester.year,
        })
    # TODO: Replace with `get_gradebook_url` after migrating to jinja2
    def get_gradebook_csv_url(self):
        return reverse("gradebook:markssheet_teacher_csv", kwargs={
            "course_slug": self.meta_course.slug,
            "city": self.get_city(),
            "semester_type": self.semester.type,
            "semester_year": self.semester.year,
        })

    def get_city(self):
        return self.city_id

    def get_city_timezone(self):
        return settings.TIME_ZONES[self.city_id]

    @property
    def city_aware_field_name(self):
        return self.__class__.city.field.name

    def has_unread(self):
        from notifications.middleware import get_unread_notifications_cache
        cache = get_unread_notifications_cache()
        return self in cache.courseoffering_news

    @property
    def has_classes_with_video(self):
        return self.materials_video

    @property
    def has_classes_with_slides(self):
        return self.materials_slides

    @property
    def has_classes_with_files(self):
        return self.materials_files

    @property
    def is_completed(self):
        return self.completed_at <= now_local(self.get_city_timezone()).date()

    @property
    def in_current_term(self):
        current_term_index = get_current_term_index(self.get_city_timezone())
        return self.semester.index == current_term_index

    @property
    def enrollment_is_open(self):
        if self.is_open:
            return True
        if self.is_completed:
            return False
        city_tz = self.get_city_timezone()
        today = now_local(city_tz).date()
        start_at = self.semester.enrollment_start_at
        return start_at <= today <= self.semester.enrollment_end_at

    @property
    def is_capacity_limited(self):
        return self.capacity > 0

    @cached_property
    def places_left(self):
        """Returns how many places left if the number is limited"""
        if self.is_capacity_limited:
            active_enrollments = self.enrollment_set(manager="active").count()
            return max(0, self.capacity - active_enrollments)
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

    def get_reviews(self):
        """Collect reviews from passed courses"""
        return self.__class__.objects.reviews_for_course(self)


class CourseTeacher(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE)
    course = models.ForeignKey(
        Course,
        related_name="course_teachers",
        on_delete=models.CASCADE)
    roles = BitField(flags=(
        ('lecturer', _('Lecturer')),
        ('reviewer', _('Reviewer')),
    ), default=('lecturer',))
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


class CourseNews(TimeStampedModel):
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

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.course.field.name

    def get_update_url(self):
        return city_aware_reverse('course_news_update', kwargs={
            "course_slug": self.course.meta_course.slug,
            "semester_slug": self.course.semester.slug,
            "city_code": self.get_city(),
            "pk": self.pk
        })

    def get_stats_url(self):
        return city_aware_reverse('course_news_unread', kwargs={
            "course_slug": self.course.meta_course.slug,
            "semester_slug": self.course.semester.slug,
            "city_code": self.get_city(),
            "news_pk": self.pk
        })

    def get_delete_url(self):
        return city_aware_reverse('course_news_delete', kwargs={
            "course_slug": self.course.meta_course.slug,
            "semester_slug": self.course.semester.slug,
            "city_code": self.get_city(),
            "pk": self.pk
        })

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_city_timezone()
        return timezone.localtime(self.created, timezone=tz)


def course_class_slides_upload_to(instance: "CourseClass", filename) -> str:
    """
    Generates path to uploaded slides. Filename could have collisions if
    more than one class of the same type in a day.

    Format:
        courses/<term_slug>/<city>-<course_slug>/slides/<generated_filename>

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
                        f"{course.city_id}-{course_slug}",
                        "slides", filename)


class CourseClass(TimeStampedModel):
    course = models.ForeignKey(
        Course,
        verbose_name=_("Course"),
        on_delete=models.PROTECT)
    venue = models.ForeignKey(
        Venue,
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

    objects = CourseClassQuerySet.as_manager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_track_fields()

    def __str__(self):
        return smart_text(self.name)

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.course.field.name

    def get_absolute_url(self):
        return city_aware_reverse('class_detail', kwargs={
           "city_code": self.get_city(),
           "course_slug": self.course.meta_course.slug,
           "semester_slug": self.course.semester.slug,
           "pk": self.pk
        })

    def get_update_url(self):
        return city_aware_reverse('course_class_update', kwargs={
            "course_slug": self.course.meta_course.slug,
            "semester_slug": self.course.semester.slug,
            "city_code": self.get_city(),
            "pk": self.pk
        })

    def get_delete_url(self):
        return city_aware_reverse('course_class_delete', kwargs={
            "course_slug": self.course.meta_course.slug,
            "semester_slug": self.course.semester.slug,
            "city_code": self.get_city(),
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
        course = self.course
        course.compute_fields(prefetch=True)

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
    Path format: courses/<term_slug>/<city>-<course_slug>/materials/<filename>

    Example:
        courses/2018-autumn/spb-data-bases/materials/Лекция_1.pdf
    """
    course = instance.course_class.course
    course_slug = course.meta_course.slug
    filename = filename.replace(" ", "_")
    # TODO: transliterate?
    return os.path.join("courses", course.semester.slug,
                        f"{course.city_id}-{course_slug}",
                        "materials", filename)


class CourseClassAttachment(TimeStampedModel):
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
            course.compute_fields('materials_files', prefetch=True)

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.course_class.field.name

    def get_delete_url(self):
        return city_aware_reverse('course_class_attachment_delete', kwargs={
            "course_slug": self.course_class.course.meta_course.slug,
            "semester_slug": self.course_class.course.semester.slug,
            "city_code": self.get_city(),
            "class_pk": self.course_class.pk,
            "pk": self.pk
        })

    @property
    def material_file_name(self):
        return os.path.basename(self.material.name)


class Assignment(TimeStampedModel):
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

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.course.field.name

    def deadline_at_local(self, tz=None):
        if not tz:
            tz = self.get_city_timezone()
        return timezone.localtime(self.deadline_at, timezone=tz)

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_city_timezone()
        return timezone.localtime(self.created, timezone=tz)

    def get_teacher_url(self):
        return reverse('assignment_detail_teacher', kwargs={"pk": self.pk})

    def get_update_url(self):
        return city_aware_reverse('assignment_update', kwargs={
            "course_slug": self.course.meta_course.slug,
            "semester_slug": self.course.semester.slug,
            "city_code": self.get_city(),
            "pk": self.pk
        })

    def get_delete_url(self):
        return city_aware_reverse('assignment_delete', kwargs={
            "course_slug": self.course.meta_course.slug,
            "semester_slug": self.course.semester.slug,
            "city_code": self.get_city(),
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
        return reverse("assignment_attachments_download", kwargs={
            "sid": hashids.encode(ASSIGNMENT_TASK_ATTACHMENT, self.pk),
            "file_name": self.file_name
        })

    def get_delete_url(self):
        return city_aware_reverse('assignment_attachment_delete', kwargs={
            "course_slug": self.assignment.course.meta_course.slug,
            "semester_slug": self.assignment.course.semester.slug,
            "assignment_pk": self.assignment.pk,
            "pk": self.pk,
            "city_code": self.assignment.course.get_city(),
        })
