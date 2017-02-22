# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
import logging
import os.path
import time

from bitfield import BitField
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import smart_text, python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.timezone import utc, now
from django.utils.translation import ugettext_lazy as _
from micawber.contrib.mcdjango import extract_oembed
from model_utils import Choices, FieldTracker
from model_utils.fields import MonitorField, StatusField
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel, TimeFramedModel
from sorl.thumbnail import ImageField

from core.models import LATEX_MARKDOWN_HTML_ENABLED, City
from core.notifications import get_unread_notifications_cache
from core.utils import hashids
from learning import settings as learn_conf
from learning.settings import PARTICIPANT_GROUPS, GRADES, SHORT_GRADES, \
    SEMESTER_TYPES, GRADING_TYPES
from .utils import get_current_semester_pair, \
    get_term_index, convert_term_start_to_datetime, get_term_start

logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class Course(TimeStampedModel):
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
        return reverse('course_detail', args=[self.slug])


@python_2_unicode_compatible
class Semester(models.Model):
    TYPES = SEMESTER_TYPES

    year = models.PositiveSmallIntegerField(
        _("Year"),
        validators=[MinValueValidator(1990)])
    type = StatusField(verbose_name=_("Semester|type"),
                       choices_name='TYPES')
    enroll_before = models.DateField(
        _("Enroll before"),
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

        Now helps to validate class date range in `CourseClassForm`
        """
        return get_term_start(self.year, self.type)

    @cached_property
    def ends_at(self):
        if self.type == 'spring':
            next_start_str = learn_conf.SUMMER_TERM_START
            next_year = self.year
        elif self.type == 'summer':
            next_start_str = learn_conf.AUTUMN_TERM_START
            next_year = self.year
        else:
            next_start_str = learn_conf.SPRING_TERM_START
            next_year = self.year + 1
        return convert_term_start_to_datetime(next_year, next_start_str) \
               - datetime.timedelta(days=1)

    @classmethod
    def get_current(cls):
        year, season = get_current_semester_pair()
        obj, created = cls.objects.get_or_create(year=year,
                                                 type=season)
        if created:
            obj.save()
        return obj

    def is_current(self):
        year, term = get_current_semester_pair()
        return year == self.year and term == self.type

    def save(self, *args, **kwargs):
        self.index = get_term_index(self.year, self.type)
        super(Semester, self).save(*args, **kwargs)

    def get_academic_year(self):
        """Academic year starts from autumn term"""
        if self.type == SEMESTER_TYPES.autumn:
            return self.year
        else:
            return self.year - 1


class CustomCourseOfferingQuerySet(models.QuerySet):
    def site_related(self, request):
        qs = self.filter(city__pk=request.city_code)
        if request.site.domain == settings.CLUB_DOMAIN:
            qs = qs.filter(is_open=True,)
        return qs


@python_2_unicode_compatible
class CourseOffering(TimeStampedModel):
    objects = models.Manager()
    custom = CustomCourseOfferingQuerySet.as_manager()
    course = models.ForeignKey(
        Course,
        verbose_name=_("Course"),
        on_delete=models.PROTECT)
    # TODO: hide in admin?
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
        through='CourseOfferingTeacher')
    semester = models.ForeignKey(
        Semester,
        verbose_name=_("Semester"),
        on_delete=models.PROTECT)
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
    is_published_in_video = models.BooleanField(
        _("Published in video section"),
        default=False)
    is_open = models.BooleanField(
        _("Open course offering"),
        help_text=_("This course offering will be available on Computer"
                    "Science Club website so anyone can join"),
        default=False)
    is_completed = models.BooleanField(
        _("Course already completed"),
        default=False)
    enrolled_students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Enrolled students"),
        related_name='enrolled_on_set',
        blank=True,
        through='Enrollment')
    city = models.ForeignKey(City, default=settings.DEFAULT_CITY_CODE)
    language = models.CharField(max_length=5, db_index=True,
                                choices=settings.LANGUAGES,
                                default=settings.LANGUAGE_CODE)

    class Meta(object):
        ordering = ["-semester", "course__created"]
        verbose_name = _("Course offering")
        verbose_name_plural = _("Course offerings")

    def __str__(self):
        return "{0}, {1}".format(smart_text(self.course),
                                 smart_text(self.semester))

    def get_absolute_url(self):
        return reverse('course_offering_detail', args=[self.course.slug,
                                                       self.semester.slug])

    def get_city(self):
        return "".join(self.city_id.split(" ")[1:]).lower()

    def has_unread(self):
        cache = get_unread_notifications_cache()
        return self in cache.courseoffering_news

    # FIXME(Dmitry): refactor this to use Semester object
    @classmethod
    def by_semester(cls, semester):
        (year, season) = semester
        return cls.objects.filter(semester__type=season,
                                  semester__year=year)

    @cached_property
    def is_ongoing(self):
        current_semester = get_current_semester_pair()
        return (current_semester.year == self.semester.year
                and current_semester.type == self.semester.type)

    def enrollment_opened(self):
        if self.is_open:
            return True
        if self.is_completed or not self.is_ongoing:
            return False
        today = timezone.now()
        if self.semester.enroll_before:
            enroll_before_date = self.semester.enroll_before
            enroll_before = datetime.datetime(
                year=enroll_before_date.year,
                month=enroll_before_date.month,
                day=enroll_before_date.day,
                tzinfo=utc
            )
            enroll_before += datetime.timedelta(days=1)
        else:
            year, term_type = get_current_semester_pair()
            current_term_start = get_term_start(year, term_type)
            enroll_before = current_term_start + datetime.timedelta(
                days=learn_conf.ENROLLMENT_DURATION)
        if today > enroll_before:
            return False
        return True

    def is_capacity_limited(self):
        return self.capacity > 0

    @cached_property
    def places_left(self):
        """Returns how many places left if the number is limited"""
        if self.is_capacity_limited():
            return max(0, self.capacity - self.enrollment_set.count())
        else:
            return float("inf")


@python_2_unicode_compatible
class CourseOfferingTeacher(models.Model):
    # XXX: limit choices on admin form level due to bug https://code.djangoproject.com/ticket/11707
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL)
    course_offering = models.ForeignKey(CourseOffering)
    roles = BitField(flags=(
        ('lecturer', _('Lecturer')),
        ('reviewer', _('Reviewer')),
    ), default=('lecturer',))
    notify_by_default = models.BooleanField(
        _("Notify by default"),
        help_text=(_("Add teacher to assignment notify settings by default")),
        default=False)

    class Meta:
        verbose_name = _("Course Offering teacher")
        verbose_name_plural = _("Course Offering teachers")
        unique_together = [['teacher', 'course_offering']]

    def __str__(self):
        return "{0} [{1}]".format(smart_text(self.teacher),
                                  smart_text(self.course_offering_id))

    @property
    def is_lecturer(self):
        return bool(self.roles.lecturer)

    @staticmethod
    def grouped(course_teachers):
        """
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


@python_2_unicode_compatible
class CourseOfferingNews(TimeStampedModel):
    course_offering = models.ForeignKey(
        CourseOffering,
        verbose_name=_("Course offering"),
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
                                  smart_text(self.course_offering))


@python_2_unicode_compatible
class Venue(models.Model):
    city = models.ForeignKey(City, null=True, blank=True, \
                             default=settings.DEFAULT_CITY_CODE)
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
    is_preferred = models.BooleanField(
        _("Preferred"),
        help_text=(_("Will be displayed on top of the venue list")),
        default=False)

    class Meta:
        ordering = ["-is_preferred", "name"]
        verbose_name = _("Venue")
        verbose_name_plural = _("Venues")

    def __str__(self):
        return "{0}".format(smart_text(self.name))

    def get_absolute_url(self):
        return reverse('venue_detail', args=[self.pk])


def courseclass_slides_file_name(self, filename):
    _, ext = os.path.splitext(filename)
    timestamp = self.date.strftime("%Y_%m_%d")
    course_offering = ("{0}_{1}"
                       .format(self.course_offering.course.slug,
                               self.course_offering.semester.slug)
                       .replace("-", "_"))
    filename = ("{0}_{1}{2}"
                .format(timestamp,
                        course_offering,
                        ext))
    return os.path.join('slides', course_offering, filename)


@python_2_unicode_compatible
class CourseClass(TimeStampedModel, object):
    TYPES = Choices(('lecture', _("Lecture")),
                    ('seminar', _("Seminar")))

    course_offering = models.ForeignKey(
        CourseOffering,
        verbose_name=_("Course offering"),
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
        ordering = ["-date", "course_offering", "-starts_at"]
        verbose_name = _("Class")
        verbose_name_plural = _("Classes")

    def __str__(self):
        return smart_text(self.name)

    def get_absolute_url(self):
        return reverse('class_detail',
                       args=[self.course_offering.course.slug,
                             self.course_offering.semester.slug,
                             self.pk])

    @property
    def track_fields(self):
        return ("slides",)

    def update_track_fields(self):
        for field in self.track_fields:
            setattr(self, '_original_%s' % field, getattr(self, field))

    def get_track_field(self, field):
        return getattr(self, '_original_{}'.format(field))

    def clean(self):
        super(CourseClass, self).clean()
        # ends_at should be later than starts_at
        if self.starts_at >= self.ends_at:
            raise ValidationError(_("Class should end after it started"))

    def save(self, *args, **kwargs):
        # It's worth mentioning that logic with tracked fields and post save really complicated
        # TODO: Delegate upload slides logic to task manager
        if self.slides != self.get_track_field("slides"):
            # TODO: Maybe we should try to delete old slides from slideshare
            # TODO: Add tags to uploaded slides and we can do it
            self.slides_url = ""
        super(CourseClass, self).save()
        self.update_track_fields()

    # this is needed to properly set up fields for admin page
    def type_display_prop(self):
        return self.TYPES[self.type]

    type_display_prop.short_description = _("Type")
    type_display_prop.admin_order_field = 'type'
    type_display = property(type_display_prop)

    def video_oembed(self):
        if not self.video_url:
            return ""
        cache_key = make_template_fragment_key('video_oembed',
                                               [self.pk, self.video_url])
        embed = cache.get(cache_key)
        if not embed:
            try:
                [(_url, embed)] = extract_oembed(self.video_url)
                cache.set(cache_key, embed, 3600 * 2)
            except ValueError:
                logger.info("Extract oembed error. Return default iframe")
                iframe_template = """<iframe src={} allowfullscreen=1
                    width="{}" height="{}"></iframe>"""
                embed = {
                    "html": iframe_template.format(
                        self.video_url,
                        settings.MICAWBER_DEFAULT_SETTINGS["maxwidth"],
                        settings.MICAWBER_DEFAULT_SETTINGS["maxheight"])
                }
        return embed

    # TODO: test this
    # Note(lebedev): should be a manager, not a class method.
    @classmethod
    def by_semester(cls, semester):
        (year, season) = semester
        return cls.objects.filter(
            course_offering__semester__type=season,
            course_offering__semester__year=year)

    @property
    def slides_file_name(self):
        return os.path.basename(self.slides.name)


@python_2_unicode_compatible
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

    @property
    def material_file_name(self):
        return os.path.basename(self.material.name)


@python_2_unicode_compatible
class Assignment(TimeStampedModel, object):
    course_offering = models.ForeignKey(
        CourseOffering,
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
    # FIXME: rename this to "name"
    title = models.CharField(_("Asssignment|name"),
                             max_length=140)
    text = models.TextField(_("Assignment|text"),
                            help_text=LATEX_MARKDOWN_HTML_ENABLED)
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
        CourseOfferingTeacher,
        verbose_name=_("Assignment|notify_settings"),
        help_text=_(
            "Leave blank if you want populate teachers from course offering settings"),
        blank=True)

    tracker = FieldTracker(fields=['deadline_at'])

    class Meta:
        ordering = ["created", "course_offering"]
        verbose_name = _("Assignment")
        verbose_name_plural = _("Assignments")

    def __init__(self, *args, **kwargs):
        super(Assignment, self).__init__(*args, **kwargs)
        if self.pk:
            self._original_course_offering_id = self.course_offering_id

    def clean(self):
        if (self.pk and
                    self._original_course_offering_id != self.course_offering_id):
            raise ValidationError(_("Course offering modification "
                                    "is not allowed"))
        if self.grade_min > self.grade_max:
            raise ValidationError(_("Mininum grade should be lesser than "
                                    "(or equal to) maximum one"))

    def __str__(self):
        return "{0} ({1})".format(smart_text(self.title),
                                  smart_text(self.course_offering))

    def has_unread(self):
        cache = get_unread_notifications_cache()
        return self.id in cache.assignment_ids_set

    @property
    def is_open(self):
        return self.deadline_at > timezone.now()

    @property
    def attached_file_name(self):
        return os.path.basename(self.attached_file.name)

    def deadline_at__date(self):
        return self.deadline_at.strftime('%d.%m.%Y')


def assignmentattach_upload_to(instance, filename):
    return ("assignment_{0}/attachments/{1}".format(
        instance.assignment_id, filename))


@python_2_unicode_compatible
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
        return reverse(
            "assignment_attachments_download",
            args=[
                hashids.encode(learn_conf.ASSIGNMENT_TASK_ATTACHMENT, self.pk)]
        )


@python_2_unicode_compatible
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

    assignment = models.ForeignKey(
        Assignment,
        verbose_name=_("StudentAssignment|assignment"),
        on_delete=models.CASCADE)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("StudentAssignment|student"),
        on_delete=models.CASCADE,
        limit_choices_to={'groups__pk': PARTICIPANT_GROUPS.STUDENT_CENTER})
    grade = models.PositiveSmallIntegerField(
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
        if self.grade > self.assignment.grade_max:
            raise ValidationError(_("Grade can't be larger than maximum "
                                    "one ({0})")
                                  .format(self.assignment.grade_max))

    def __str__(self):
        return "{0} - {1}".format(smart_text(self.assignment),
                                  smart_text(self.student.get_full_name()))

    def has_unread(self):
        cache = get_unread_notifications_cache()
        return self in cache.assignments

    @cached_property
    def state(self):
        grade_min = self.assignment.grade_min
        grade_max = self.assignment.grade_max
        return self.calculate_state(self.grade, self.assignment.is_online,
                                    self.is_passed, grade_min, grade_max)

    @staticmethod
    def calculate_state(grade, is_online, is_passed, grade_min, grade_max):
        grade_range = grade_max - grade_min
        if grade is None:
            if not is_online or is_passed:
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

    # FIXME: rename
    @property
    def is_passed(self):
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


@python_2_unicode_compatible
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
        return ("Comment to {0} by {1}"
                .format(smart_text(self.student_assignment
                                   .assignment),
                        smart_text(self.student_assignment
                                   .student.get_full_name())))

    @property
    def attached_file_name(self):
        return os.path.basename(self.attached_file.name)

    def attached_file_url(self):
        return reverse(
            "assignment_attachments_download",
            args=[hashids.encode(
                learn_conf.ASSIGNMENT_COMMENT_ATTACHMENT,
                self.pk)]
        )

    def is_stale_for_edit(self):
        # Teacher can edit comment during 10 min period only
        return (now() - self.created).total_seconds() > 600


class SiteRelatedEnrollmentQuerySet(models.QuerySet):
    def site_related(self, request):
        qs = self.select_related("course_offering").filter(
            course_offering__city__pk=request.city_code)
        if request.site.domain == settings.CLUB_DOMAIN:
            qs = qs.filter(course_offering__is_open=True)
        return qs


@python_2_unicode_compatible
class Enrollment(TimeStampedModel):
    GRADES = GRADES
    objects = models.Manager()
    custom = SiteRelatedEnrollmentQuerySet.as_manager()

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)
    course_offering = models.ForeignKey(
        CourseOffering,
        verbose_name=_("Course offering"),
        on_delete=models.CASCADE)
    grade = StatusField(
        verbose_name=_("Enrollment|grade"),
        choices_name='GRADES',
        default='not_graded')
    grade_changed = MonitorField(
        verbose_name=_("Enrollment|grade changed"),
        monitor='grade')

    class Meta:
        ordering = ["student", "course_offering"]
        unique_together = [('student', 'course_offering')]
        verbose_name = _("Enrollment")
        verbose_name_plural = _("Enrollments")

    def clean(self):
        if not self.student.is_student:
            raise ValidationError(_("Only students can enroll to courses"))

    def __str__(self):
        return "{0} - {1}".format(smart_text(self.course_offering),
                                  smart_text(self.student.get_full_name()))

    @property
    def grade_display(self):
        return GRADES[self.grade]

    @property
    def grade_honest(self):
        """Show `satisfactory` instead of `pass` for default grading type"""
        if (self.course_offering.grading_type == GRADING_TYPES.default and
                self.grade == getattr(GRADES, 'pass')):
            return _("Satisfactory")
        return GRADES[self.grade]

    @property
    def grade_short(self):
        return SHORT_GRADES[self.grade]


@python_2_unicode_compatible
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


@python_2_unicode_compatible
class CourseOfferingNewsNotification(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("User"),
        on_delete=models.CASCADE)
    course_offering_news = models.ForeignKey(
        CourseOfferingNews,
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


@python_2_unicode_compatible
class NonCourseEvent(TimeStampedModel):
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
        super(NonCourseEvent, self).clean()
        # ends_at should be later than starts_at
        if self.starts_at >= self.ends_at:
            raise ValidationError(_("Event should end after it's start"))

    # this is needed to share code between CourseClasses and this model
    @property
    def type(self):
        return "noncourse"

    def get_absolute_url(self):
        return reverse('non_course_event_detail', args=[self.pk])


@python_2_unicode_compatible
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


class StudyProgram(models.Model):
    name = models.CharField(_("StudyProgram|Name"), max_length=255)
    year = models.PositiveSmallIntegerField(
        _("Year"), validators=[MinValueValidator(1990)])
    city = models.ForeignKey(City,
                             verbose_name=_("City"),
                             default=settings.DEFAULT_CITY_CODE)
    area = models.ForeignKey(AreaOfStudy, verbose_name=_("Area of Study"))
    description = models.TextField(
        _("StudyProgram|description"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)

    class Meta:
        verbose_name = _("Study Program")
        verbose_name_plural = _("Study Programs")

    def __str__(self):
        return smart_text(self.name)


class StudyProgramCourse(models.Model):
    course = models.ForeignKey(
        Course,
        verbose_name=_("Course"),
        on_delete=models.PROTECT)
    study_program = models.ForeignKey(
        StudyProgram,
        verbose_name=_("Study Program"),
        on_delete=models.PROTECT)
    group = models.PositiveSmallIntegerField(
        _("Group"), help_text=_("Courses within the same group are combined "
                                "using the boolean OR."))

    class Meta:
        verbose_name = _("Study Program Course")
        verbose_name_plural = _("Study Program Courses")

    def __str__(self):
        return smart_text("#{}".format(self.pk))


@python_2_unicode_compatible
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


@python_2_unicode_compatible
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


@python_2_unicode_compatible
class Useful(models.Model):
    question = models.CharField(_("Question"), max_length=255)
    answer = models.TextField(_("Answer"))
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
                             default=settings.CENTER_SITE_ID)

    class Meta:
        ordering = ["sort"]
        verbose_name = _("Useful")
        verbose_name_plural = _("Useful")

    def __str__(self):
        return smart_text(self.question)


@python_2_unicode_compatible
class Internship(TimeStampedModel):
    question = models.CharField(_("Question"), max_length=255)
    answer = models.TextField(_("Answer"))
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
                             default=settings.CENTER_SITE_ID)

    class Meta:
        ordering = ["sort"]
        verbose_name = _("Internship")
        verbose_name_plural = _("Internships")

    def __str__(self):
        return smart_text(self.question)
