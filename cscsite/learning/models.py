# -*- coding: utf-8 -*-

import datetime
import logging
import os.path
import time

import pytz
from bitfield import BitField
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import smart_text, python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices, FieldTracker
from model_utils.fields import MonitorField, StatusField
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel, TimeFramedModel
from sorl.thumbnail import ImageField

from core.db.models import GradeField
from core.models import LATEX_MARKDOWN_HTML_ENABLED, City
from core.notifications import get_unread_notifications_cache
from core.utils import hashids, city_aware_reverse
from learning import settings as learn_conf
from learning.managers import StudyProgramQuerySet, \
    CourseDefaultManager, EnrollmentDefaultManager, \
    EnrollmentActiveManager, NonCourseEventQuerySet, CourseClassQuerySet, \
    StudentAssignmentManager, AssignmentManager, CourseTeacherManager
from learning.micawber_providers import get_oembed_html
from learning.settings import GRADES, SHORT_GRADES, \
    SEMESTER_TYPES, GRADING_TYPES
from learning.tasks import maybe_upload_slides_yandex
from learning.utils import get_current_term_index, now_local, \
    next_term_starts_at
from .utils import get_current_term_pair, \
    get_term_index, get_term_start

logger = logging.getLogger(__name__)


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


class Semester(models.Model):
    TYPES = SEMESTER_TYPES

    year = models.PositiveSmallIntegerField(
        _("Year"),
        validators=[MinValueValidator(1990)])
    type = StatusField(verbose_name=_("Semester|type"),
                       choices_name='TYPES')
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
        return "{0} {1}".format(self.TYPES[self.type], self.year)

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
            lifetime = datetime.timedelta(days=learn_conf.ENROLLMENT_DURATION)
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
        if self.type == SEMESTER_TYPES.autumn:
            return self.year
        else:
            return self.year - 1


class Course(TimeStampedModel):
    objects = CourseDefaultManager()
    meta_course = models.ForeignKey(
        MetaCourse,
        verbose_name=_("Course"),
        on_delete=models.PROTECT)
    grading_type = models.SmallIntegerField(
        verbose_name=_("CourseOffering|grading_type"),
        choices=GRADING_TYPES,
        default=GRADING_TYPES.default)
    capacity = models.PositiveSmallIntegerField(
        verbose_name=_("CourseOffering|capacity"),
        default=0,
        help_text=_("0 - unlimited"))
    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Course|teachers"),
        related_name='teaching_set',
        through='learning.CourseTeacher')
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
    # Composite fields, depends on course class materials only
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

    class Meta:
        ordering = ["-semester", "meta_course__created"]
        verbose_name = _("Course offering")
        verbose_name_plural = _("Course offerings")
        unique_together = [('meta_course', 'semester', 'city')]

    def __str__(self):
        return "{0}, {1}".format(smart_text(self.meta_course),
                                 smart_text(self.semester))

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
            url_name = "markssheet_teacher_csv"
        else:
            url_name = "markssheet_teacher"
        return reverse(url_name, kwargs={
            "course_slug": self.meta_course.slug,
            "city": self.get_city(),
            "semester_type": self.semester.type,
            "semester_year": self.semester.year,
        })
    # TODO: Replace with `get_gradebook_url` after migrating to jinja2
    def get_gradebook_csv_url(self):
        return reverse("markssheet_teacher_csv", kwargs={
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
    def grading_type_css_mixin(self):
        if self.grading_type == GRADING_TYPES.binary:
            return "__binary"
        return ""

    def recalculate_grading_type(self):
        es = (Enrollment.active
              .filter(course=self)
              .values_list("grade", flat=True))
        grading_type = GRADING_TYPES.default
        if not any(g for g in es if g in [GRADES.good, GRADES.excellent]):
            grading_type = GRADING_TYPES.binary
        if self.grading_type != grading_type:
            self.grading_type = grading_type
            self.save()

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

    def failed_by_student(self, student, enrollment=None) -> bool:
        if self.is_open or not self.is_completed:
            return False
        # Checks that student didn't fail the completed course
        bad_grades = [Enrollment.GRADES.unsatisfactory,
                      Enrollment.GRADES.not_graded]
        if enrollment:
            return enrollment.grade in bad_grades
        return (Enrollment.active
                .filter(student_id=student.pk,
                        course_id=self.pk,
                        grade__in=bad_grades)
                .exists())


class CourseTeacher(models.Model):
    # XXX: limit choices on admin form level due to bug https://code.djangoproject.com/ticket/11707
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
        self._create_notifications(created)

    def _create_notifications(self, created):
        if not created:
            return
        co_id = self.course_id
        notifications = []
        active_enrollments = Enrollment.active.filter(course_id=co_id)
        # Replace cached queryset with .bulk_create() + .iterator()
        for e in active_enrollments.iterator():
            notifications.append(
                CourseNewsNotification(user_id=e.student_id,
                                       course_offering_news_id=self.pk))
        teachers = CourseTeacher.objects.filter(course_id=co_id)
        for co_t in teachers.iterator():
            notifications.append(
                CourseNewsNotification(user_id=co_t.teacher_id,
                                       course_offering_news_id=self.pk))
        CourseNewsNotification.objects.bulk_create(notifications)

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_city_timezone()
        return timezone.localtime(self.created, timezone=tz)


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


def courseclass_slides_file_name(self, filename):
    _, ext = os.path.splitext(filename)
    timestamp = self.date.strftime("%Y_%m_%d")
    course = ("{0}_{1}".format(self.course.meta_course.slug,
                               self.course.semester.slug)
                       .replace("-", "_"))
    filename = ("{0}_{1}{2}".format(timestamp, course, ext))
    return os.path.join('slides', course, filename)


class CourseClass(TimeStampedModel):
    TYPES = Choices(('lecture', _("Lecture")),
                    ('seminar', _("Seminar")))

    course = models.ForeignKey(
        Course,
        verbose_name=_("Course"),
        on_delete=models.PROTECT)
    venue = models.ForeignKey(
        Venue,
        verbose_name=_("CourseClass|Venue"),
        on_delete=models.PROTECT)
    type = StatusField(
        _("Type"),
        choices_name='TYPES')
    name = models.CharField(_("CourseClass|Name"), max_length=255)
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    slides = models.FileField(
        _("Slides"),
        blank=True,
        upload_to=courseclass_slides_file_name)
    slides_url = models.URLField(_("SlideShare URL"), blank=True)
    video_url = models.URLField(_("Video URL"), blank=True,
                                help_text=_(
                                    "Both YouTube and Yandex Video are supported"))
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

    def update_composite_fields(self):
        """
        Updates composite fields used on courses list page under the assumption
        that teacher/curator never deletes materials, only adds.
        """
        update_fields = {}
        if bool(self.slides):
            update_fields["materials_slides"] = True
        if self.video_url.strip() != "":
            update_fields["materials_video"] = True
        if self.courseclassattachment_set.exists():
            update_fields["materials_files"] = True
        if update_fields:
            (Course.objects
             .filter(pk=self.course_id)
             .update(**update_fields))

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
        self.update_composite_fields()

    def video_iframe(self):
        return get_oembed_html(self.video_url, 'video_oembed',
                               use_default=True)

    def slides_iframe(self):
        return get_oembed_html(self.slides_url, 'slides_oembed',
                               use_default=False)

    @property
    def slides_file_name(self):
        return os.path.basename(self.slides.name)


class CourseClassAttachment(TimeStampedModel, object):
    course_class = models.ForeignKey(
        CourseClass,
        verbose_name=_("Class"),
        on_delete=models.CASCADE)
    material = models.FileField(upload_to="course_class_attachments")

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
            CourseClass.update_composite_fields(self.course_class)

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
    assigned_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Assignment|assigned_to"),
        blank=True,
        through='StudentAssignment')
    deadline_at = models.DateTimeField(_("Assignment|deadline"))
    is_online = models.BooleanField(_("Assignment|can be passed online"),
                                    default=True)
    title = models.CharField(_("Asssignment|name"),
                             max_length=140)
    text = models.TextField(_("Assignment|text"),
                            help_text=LATEX_MARKDOWN_HTML_ENABLED)
    # Min value to pass assignment
    grade_min = models.PositiveSmallIntegerField(
        _("Assignment|grade_min"),
        default=2,
        validators=[MaxValueValidator(1000)])
    grade_max = models.PositiveSmallIntegerField(
        _("Assignment|grade_max"),
        default=5,
        validators=[MaxValueValidator(1000)])
    # XXX: No ability to add default values with `post_save` signal in one place
    # We do it separately in admin form and AssignmentCreateView
    notify_teachers = models.ManyToManyField(
        CourseTeacher,
        verbose_name=_("Assignment|notify_settings"),
        help_text=_(
            "Leave blank if you want populate teachers from course offering settings"),
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
        if self.grade_min > self.grade_max:
            raise ValidationError(_("Minimum grade should be lesser than "
                                    "(or equal to) maximum one"))

    def __str__(self):
        return "{0} ({1})".format(smart_text(self.title),
                                  smart_text(self.course))

    def has_unread(self):
        cache = get_unread_notifications_cache()
        return self.id in cache.assignment_ids_set

    @property
    def is_open(self):
        return self.deadline_at > timezone.now()

    @property
    def attached_file_name(self):
        return os.path.basename(self.attached_file.name)


def assignmentattach_upload_to(instance, filename):
    return ("assignment_{0}/attachments/{1}".format(
        instance.assignment_id, filename))


class AssignmentAttachment(TimeStampedModel, object):
    assignment = models.ForeignKey(
        Assignment,
        verbose_name=_("Assignment"),
        on_delete=models.CASCADE)
    attachment = models.FileField(upload_to=assignmentattach_upload_to)

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
            "sid": hashids.encode(learn_conf.ASSIGNMENT_TASK_ATTACHMENT, self.pk),
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


class StudentAssignment(TimeStampedModel):
    STATES = Choices(('not_submitted', _("Assignment|not submitted")),
                     ('not_checked', _("Assignment|not checked")),
                     ('unsatisfactory', _("Assignment|unsatisfactory")),
                     ('pass', _("Assignment|pass")),
                     ('good', _("Assignment|good")),
                     ('excellent', _("Assignment|excellent")))
    SHORT_STATES = Choices(('not_submitted', "—"),
                           ('not_checked', "…"),
                           ('unsatisfactory', "2"),
                           ('pass', "3"),
                           ('good', "4"),
                           ('excellent', "5"))
    LAST_COMMENT_NOBODY = 0
    LAST_COMMENT_STUDENT = 1
    LAST_COMMENT_TEACHER = 2

    objects = StudentAssignmentManager()

    assignment = models.ForeignKey(
        Assignment,
        verbose_name=_("StudentAssignment|assignment"),
        on_delete=models.CASCADE)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("StudentAssignment|student"),
        on_delete=models.CASCADE)
    grade = GradeField(
        verbose_name=_("Grade"),
        null=True,
        blank=True)
    grade_changed = MonitorField(
        verbose_name=_("Assignment|grade changed"),
        monitor='grade')
    first_submission_at = models.DateTimeField(
        _("Assignment|first_submission"),
        null=True,
        editable=False)
    last_comment_from = models.PositiveSmallIntegerField(
        verbose_name=_("Last comment from"),
        help_text=_("0 - no comments yet, 1 - from student, 2 - from teacher"),
        editable=False,
        default=LAST_COMMENT_NOBODY)

    class Meta:
        ordering = ["assignment", "student"]
        verbose_name = _("Assignment-student")
        verbose_name_plural = _("Assignment-students")
        unique_together = [['assignment', 'student']]

    def clean(self):
        if not self.student.is_student:
            raise ValidationError(_("Student field should point to "
                                    "an actual student"))
        if self.grade and self.grade > self.assignment.grade_max:
            raise ValidationError(_("Grade can't be larger than maximum "
                                    "one ({0})")
                                  .format(self.assignment.grade_max))

    def __str__(self):
        return "{0} - {1}".format(smart_text(self.assignment),
                                  smart_text(self.student.get_full_name()))

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.assignment.field.name

    def get_teacher_url(self):
        return reverse('a_s_detail_teacher', kwargs={"pk": self.pk})

    def get_student_url(self):
        return reverse('a_s_detail_student', kwargs={"pk": self.pk})

    def has_unread(self):
        cache = get_unread_notifications_cache()
        return self.pk in cache.assignments

    def has_comments(self, user):
        return any(c.author_id == user.pk for c in
                   self.assignmentcomment_set.all())

    @cached_property
    def state(self):
        grade_min = self.assignment.grade_min
        grade_max = self.assignment.grade_max
        return self.calculate_state(self.grade, self.assignment.is_online,
                                    self.submission_is_received, grade_min, grade_max)

    @staticmethod
    def calculate_state(grade, is_online, submission_is_received, grade_min,
                        grade_max):
        grade_range = grade_max - grade_min
        if grade is None:
            if not is_online or submission_is_received:
                return 'not_checked'
            else:
                return 'not_submitted'
        else:
            if grade < grade_min or grade == 0:
                return 'unsatisfactory'
            elif grade < grade_min + 0.4 * grade_range:
                return 'pass'
            elif grade < grade_min + 0.8 * grade_range:
                return 'good'
            else:
                return 'excellent'

    @property
    def submission_is_received(self):
        """
        Returns true if we have submission from student.
        Makes sense only when assignment can be passed through site.
        """
        return self.first_submission_at is not None

    @property
    def state_display(self):
        if self.grade is not None:
            return "{0} ({1}/{2})".format(self.STATES[self.state],
                                          self.grade,
                                          self.assignment.grade_max)
        else:
            return self.STATES[self.state]

    @property
    def state_short(self):
        if self.grade is not None:
            return "{0}/{1}".format(self.grade,
                                    self.assignment.grade_max)
        else:
            return self.SHORT_STATES[self.state]


## NOTE(Dmitry): this is needed because of
## https://docs.djangoproject.com/en/1.7/topics/migrations/#serializing-values
def assignmentcomment_upload_to(instance, filename):
    return ("assignment_{0}/user_{1}/{2}/{3}"
            .format(instance.student_assignment.assignment.pk,
                    instance.student_assignment.student.pk,
                    # somewhat protecting against URL enumeration
                    int(time.time()) % 30,
                    filename))


class AssignmentComment(TimeStampedModel):
    student_assignment = models.ForeignKey(
        'StudentAssignment',
        verbose_name=_("AssignmentComment|student_assignment"),
        on_delete=models.CASCADE)
    text = models.TextField(
        _("AssignmentComment|text"),
        help_text=_("LaTeX+Markdown is enabled"),
        blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Author"),
        on_delete=models.CASCADE)
    attached_file = models.FileField(
        upload_to=assignmentcomment_upload_to,
        blank=True)

    class Meta:
        ordering = ["created"]
        verbose_name = _("Assignment-comment")
        verbose_name_plural = _("Assignment-comments")

    def __str__(self):
        return ("Comment to {0} by {1}".format(
            smart_text(self.student_assignment.assignment),
            smart_text(self.student_assignment.student.get_full_name())))

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.student_assignment.field.name

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_city_timezone()
        return timezone.localtime(self.created, timezone=tz)

    @property
    def attached_file_name(self):
        return os.path.basename(self.attached_file.name)

    def attached_file_url(self):
        return reverse("assignment_attachments_download", kwargs={
            "sid": hashids.encode(learn_conf.ASSIGNMENT_COMMENT_ATTACHMENT,
                                  self.pk),
            "file_name": self.attached_file_name
        })

    def is_stale_for_edit(self):
        # Teacher can edit comment during 10 min period only
        return (now() - self.created).total_seconds() > 600


class Enrollment(TimeStampedModel):
    GRADES = GRADES
    objects = EnrollmentDefaultManager()
    active = EnrollmentActiveManager()

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)
    course = models.ForeignKey(
        Course,
        verbose_name=_("Course offering"),
        on_delete=models.CASCADE)
    grade = StatusField(
        verbose_name=_("Enrollment|grade"),
        choices_name='GRADES',
        default='not_graded')
    grade_changed = MonitorField(
        verbose_name=_("Enrollment|grade changed"),
        monitor='grade')
    is_deleted = models.BooleanField(
        _("The student left the course"),
        default=False)
    reason_entry = models.TextField(
        _("Entry reason"),
        blank=True)
    reason_leave = models.TextField(
        _("Leave reason"),
        blank=True)

    class Meta:
        ordering = ["student", "course"]
        unique_together = [('student', 'course')]
        verbose_name = _("Enrollment")
        verbose_name_plural = _("Enrollments")

    def __str__(self):
        return "{0} - {1}".format(smart_text(self.course),
                                  smart_text(self.student.get_full_name()))

    def clean(self):
        if not self.student.is_student:
            raise ValidationError(_("Only students can enroll to courses"))

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        # TODO: Call on changing `is_deleted` flag only
        self._populate_assignments_for_new_enrolled_student(created)

    def _populate_assignments_for_new_enrolled_student(self, created):
        if self.is_deleted:
            return
        for a in self.course.assignment_set.all():
            StudentAssignment.objects.get_or_create(assignment=a,
                                                    student_id=self.student_id)

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.course.field.name

    def grade_changed_local(self, tz=None):
        if not tz:
            tz = self.get_city_timezone()
        return timezone.localtime(self.grade_changed, timezone=tz)

    @property
    def grade_display(self):
        return GRADES[self.grade]

    @property
    def grade_honest(self):
        """Show `satisfactory` instead of `pass` for default grading type"""
        if (self.course.grading_type == GRADING_TYPES.default and
                self.grade == getattr(GRADES, 'pass')):
            return _("Satisfactory")
        return GRADES[self.grade]

    @property
    def grade_short(self):
        return SHORT_GRADES[self.grade]


class AssignmentNotification(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("User"),
        on_delete=models.CASCADE)
    student_assignment = models.ForeignKey(
        'StudentAssignment',
        verbose_name=_("student_assignment"),
        on_delete=models.CASCADE)
    is_about_passed = models.BooleanField(_("About passed assignment"),
                                          default=False)
    is_about_creation = models.BooleanField(_("About created assignment"),
                                            default=False)
    is_about_deadline = models.BooleanField(_("About change of deadline"),
                                            default=False)
    is_unread = models.BooleanField(_("Unread"),
                                    default=True)
    is_notified = models.BooleanField(_("User is notified"),
                                      default=False)

    objects = models.Manager()
    unread = QueryManager(is_unread=True)

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Assignment notification")
        verbose_name_plural = _("Assignment notifications")

    def clean(self):
        if self.is_about_passed and not self.user.is_teacher:
            raise ValidationError(_("Only teachers can receive notifications "
                                    "of passed assignments"))

    def __str__(self):
        return ("notification for {0} on {1}"
                .format(smart_text(self.user.get_full_name()),
                        smart_text(self.student_assignment)))

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.student_assignment.field.name

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_city_timezone()
        return timezone.localtime(self.created, timezone=tz)


class CourseNewsNotification(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("User"),
        on_delete=models.CASCADE)
    course_offering_news = models.ForeignKey(
        CourseNews,
        verbose_name=_("Course offering news"),
        on_delete=models.CASCADE)
    is_unread = models.BooleanField(_("Unread"),
                                    default=True)
    is_notified = models.BooleanField(_("User is notified"),
                                      default=False)

    objects = models.Manager()
    unread = QueryManager(is_unread=True)

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Course offering news notification")
        verbose_name_plural = _("Course offering news notifications")

    def __str__(self):
        return ("notification for {0} on {1}"
                .format(smart_text(self.user.get_full_name()),
                        smart_text(self.course_offering_news)))


class NonCourseEvent(TimeStampedModel):
    objects = NonCourseEventQuerySet.as_manager()
    venue = models.ForeignKey(
        Venue,
        verbose_name=_("CourseClass|Venue"),
        on_delete=models.PROTECT)
    name = models.CharField(_("CourseClass|Name"), max_length=255)
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    date = models.DateField(_("Date"))
    starts_at = models.TimeField(_("Starts at"))
    ends_at = models.TimeField(_("Ends at"))

    class Meta:
        ordering = ["-date", "-starts_at", "name"]
        verbose_name = _("Non-course event")
        verbose_name_plural = _("Non-course events")

    def __str__(self):
        return "{}".format(smart_text(self.name))

    def clean(self):
        super().clean()
        # ends_at should be later than starts_at
        if self.starts_at >= self.ends_at:
            raise ValidationError(_("Event should end after it's start"))

    # this is needed to share code between CourseClasses and this model
    @property
    def type(self):
        return "noncourse"

    def get_absolute_url(self):
        return reverse('non_course_event_detail', args=[self.pk])


class AreaOfStudy(models.Model):
    code = models.CharField(_("PK|Code"), max_length=2, primary_key=True)
    name = models.CharField(_("AreaOfStudy|Name"), max_length=255)
    description = models.TextField(
        _("AreaOfStudy|description"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Area of study")
        verbose_name_plural = _("Areas of study")

    def __str__(self):
        return smart_text(self.name)


class StudyProgram(TimeStampedModel):
    year = models.PositiveSmallIntegerField(
        _("Year"), validators=[MinValueValidator(1990)])
    city = models.ForeignKey(City,
                             verbose_name=_("City"),
                             default=settings.DEFAULT_CITY_CODE,
                             on_delete=models.CASCADE)
    area = models.ForeignKey(AreaOfStudy, verbose_name=_("Area of Study"),
                             on_delete=models.CASCADE)
    description = models.TextField(
        _("StudyProgram|description"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        blank=True, null=True)

    class Meta:
        verbose_name = _("Study Program")
        verbose_name_plural = _("Study Programs")

    objects = StudyProgramQuerySet.as_manager()


class StudyProgramCourseGroup(models.Model):
    courses = models.ManyToManyField(
        MetaCourse,
        verbose_name=_("StudyProgramCourseGroup|courses"),
        help_text=_("Courses will be grouped with boolean OR"))
    study_program = models.ForeignKey(
        'StudyProgram',
        verbose_name=_("Study Program"),
        related_name='course_groups',
        on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("Study Program Course")
        verbose_name_plural = _("Study Program Courses")


# TODO: rename to MoocCourse
class OnlineCourse(TimeStampedModel, TimeFramedModel):
    name = models.CharField(_("Course|name"), max_length=255)
    teachers = models.TextField(
        _("Online Course|teachers"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    description = models.TextField(
        _("Online Course|description"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    link = models.URLField(
        _("Online Course|Link"))
    photo = ImageField(
        _("Online Course|photo"),
        upload_to="online_courses/",
        blank=True)
    is_au_collaboration = models.BooleanField(
        _("Collaboration with AY"),
        default=False)
    is_self_paced = models.BooleanField(
        _("Without deadlines"),
        default=False)

    class Meta:
        db_table = 'online_courses'
        ordering = ["name"]
        verbose_name = _("Online course")
        verbose_name_plural = _("Online courses")

    def __str__(self):
        return smart_text(self.name)

    def is_ongoing(self):
        return self.start and self.start <= timezone.now()

    @property
    def avatar_url(self):
        if self.photo:
            return self.photo.url
        return None


class InternationalSchool(TimeStampedModel):
    name = models.CharField(_("InternationalSchool|name"), max_length=255)
    link = models.URLField(
        _("InternationalSchool|Link"))
    place = models.CharField(_("InternationalSchool|place"), max_length=255)
    deadline = models.DateField(_("InternationalSchool|Deadline"))
    starts_at = models.DateField(_("InternationalSchool|Start"))
    ends_at = models.DateField(_("InternationalSchool|End"), blank=True,
                               null=True)
    has_grants = models.BooleanField(
        _("InternationalSchool|Grants"),
        default=False)

    class Meta:
        db_table = 'international_schools'
        ordering = ["name"]
        verbose_name = _("International school")
        verbose_name_plural = _("International schools")

    def __str__(self):
        return smart_text(self.name)


class Useful(models.Model):
    question = models.CharField(_("Question"), max_length=255)
    answer = models.TextField(_("Answer"))
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
                             default=settings.CENTER_SITE_ID,
                             on_delete=models.CASCADE)

    class Meta:
        ordering = ["sort"]
        verbose_name = _("Useful")
        verbose_name_plural = _("Useful")

    def __str__(self):
        return smart_text(self.question)


class InternshipCategory(models.Model):
    name = models.CharField(_("Category name"), max_length=255)
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
                             default=settings.CENTER_SITE_ID,
                             on_delete=models.CASCADE)

    class Meta:
        ordering = ["sort"]
        verbose_name = _("Internship category")
        verbose_name_plural = _("Internship categories")

    def __str__(self):
        return smart_text(self.name)


class Internship(TimeStampedModel):
    question = models.CharField(_("Question"), max_length=255)
    answer = models.TextField(_("Answer"))
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    category = models.ForeignKey(InternshipCategory,
                                 verbose_name=_("Internship category"),
                                 null=True,
                                 blank=True,
                                 on_delete=models.SET_NULL)

    class Meta:
        ordering = ["sort"]
        verbose_name = _("Internship")
        verbose_name_plural = _("Internships")

    def __str__(self):
        return smart_text(self.question)
