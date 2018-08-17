import logging
from random import choice
from string import ascii_lowercase, digits
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.encoding import smart_text, python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.text import normalize_newlines
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField
from model_utils import Choices
from model_utils.fields import MonitorField, StatusField, AutoLastModifiedField
from model_utils.models import TimeStampedModel
from sorl.thumbnail import ImageField, get_thumbnail
from sorl.thumbnail.images import DummyImageFile

from ajaxuploader.utils import photo_thumbnail_cropbox
from core.models import LATEX_MARKDOWN_ENABLED, City
from core.utils import is_club_site, en_to_ru_mapping
from cscenter.utils import PublicRoute
from learning.models import Semester, Enrollment
from learning.settings import PARTICIPANT_GROUPS, STUDENT_STATUS, GRADES
from learning.utils import is_positive_grade, is_negative_grade
from learning.permissions import LearningPermissionsMixin
from users.thumbnails import BoyStubImage, GirlStubImage, BaseStubImage
from .managers import CustomUserManager

# See 'https://help.yandex.ru/pdd/additional/mailbox-alias.xml'.
YANDEX_DOMAINS = ["yandex.ru", "narod.ru", "yandex.ua",
                  "yandex.by", "yandex.kz", "ya.ru", "yandex.com"]


logger = logging.getLogger(__name__)

# Github username may only contain alphanumeric characters or
# single hyphens, and cannot begin or end with a hyphen
GITHUB_ID_VALIDATOR = RegexValidator(regex="^[a-zA-Z0-9](-?[a-zA-Z0-9])*$")


# TODO: Add tests. Looks Buggy
class MonitorStatusField(models.ForeignKey):
    """
    Monitor another field of the model and logging changes.
    Reset monitoring field value by log cls after log entry was added to DB.

    How it works:
        Save db state after model init or synced with db.
        When monitored field changed (depends on prev value and `when` attrs
        update monitoring field value, add log entry
    Args:
        logging_model (cls):
            Model responsible for logging.
        monitor (string):
            Monitored field name
        when (iter):
            If monitored field get values from `when` attribute, monitoring
            field updated. Defaults to None, allows all values. [Optional]
    """

    def __init__(self, *args, **kwargs):
        cls_name = self.__class__.__name__
        self.logging_model = kwargs.pop('logging_model', None)
        if not self.logging_model:
            raise TypeError('%s requires a "logging_model" argument' % cls_name)
        self.monitored = kwargs.pop('monitored', None)
        if not self.monitored:
            raise TypeError('%s requires a "monitor" argument' % cls_name)
        when = kwargs.pop('when', None)
        if when is not None:
            when = set(when)
        self.when = when
        super().__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        # Add attribute to model instance after initialization
        self.monitored_attrname = '_monitored_%s' % name
        models.signals.post_init.connect(self._save_initial, sender=cls)
        super().contribute_to_class(cls, name, **kwargs)

    def get_monitored_value(self, instance):
        return getattr(instance, self.monitored)

    def _save_initial(self, sender, instance, **kwargs):
        if self.monitored in instance.get_deferred_fields():
            return
        setattr(instance, self.monitored_attrname,
                self.get_monitored_value(instance))

    def pre_save(self, model_instance, add):
        monitored_prev = getattr(model_instance, self.monitored_attrname)
        monitored_current = self.get_monitored_value(model_instance)
        if monitored_prev != monitored_current:
            if self.when is None or monitored_current in self.when:
                log_model = self.create_log_entry(model_instance, add)
                setattr(model_instance, self.attname, log_model.pk)
                self._save_initial(model_instance.__class__, model_instance)
        return super(MonitorStatusField, self).pre_save(model_instance, add)

    def create_log_entry(self, instance, new_model):
        if new_model:
            return False
        attrs = {self.monitored: self.get_monitored_value(instance)}
        instance_fields = [f.attname for f in instance._meta.fields]
        for field in self.logging_model._meta.fields:
            # Do not override PK
            if isinstance(field, models.AutoField):
                continue
            if field.attname not in instance_fields:
                continue
            attrs[field.attname] = getattr(instance, field.attname)
        model = self.logging_model(**attrs)
        model.prepare_fields(instance, self.attname)
        model.save()
        return model

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['monitored'] = self.monitored
        kwargs['logging_model'] = self.logging_model
        if self.when is not None:
            kwargs['when'] = self.when
        return name, path, args, kwargs


@python_2_unicode_compatible
class CSCUserStatusLog(models.Model):
    created = models.DateField(_("created"), default=now)
    semester = models.ForeignKey(
        "learning.Semester",
        verbose_name=_("Semester"),
        on_delete=models.CASCADE)
    status = models.CharField(
        choices=STUDENT_STATUS,
        verbose_name=_("Status"),
        max_length=15)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)

    class Meta:
        ordering = ['-pk']

    def prepare_fields(self, monitored_instance, monitoring_field_attname):
        if not self.student_id:
            self.student_id = monitored_instance.pk
        # Prevent additional queries in admin
        if not self.semester_id:
            self.semester_id = Semester.get_current().pk

    def __str__(self):
        return smart_text(
            "{} [{}]".format(self.student.get_full_name(True), self.semester))


class CSCUser(LearningPermissionsMixin, AbstractUser):

    group = PARTICIPANT_GROUPS

    STATUS = STUDENT_STATUS

    # TODO: django migrations can't automatically change CharField to Integer
    # Investigate how to do it manually with migrations only, then replace first param with int
    COURSES = Choices(
        ("1", 'BACHELOR_SPECIALITY_1', _('1 course bachelor, speciality')),
        ("2", 'BACHELOR_SPECIALITY_2', _('2 course bachelor, speciality')),
        ("3", 'BACHELOR_SPECIALITY_3', _('3 course bachelor, speciality')),
        ("4", 'BACHELOR_SPECIALITY_4', _('4 course bachelor, speciality')),
        ("5", 'SPECIALITY_5', _('last course speciality')),
        ("6", 'MASTER_1', _('1 course magistracy')),
        ("7", 'MASTER_2', _('2 course magistracy')),
        ("8", 'POSTGRADUATE', _('postgraduate')),
        ("9", 'GRADUATE', _('graduate')),
    )

    GENDER_MALE = 'M'
    GENDER_FEMALE = 'F'
    GENDER_CHOICES = (
        (GENDER_MALE, _('Male')),
        (GENDER_FEMALE, _('Female')),
    )
    gender = models.CharField(_("Gender"), max_length=1, choices=GENDER_CHOICES)

    modified = AutoLastModifiedField(_('modified'))

    email = models.EmailField(_('email address'), unique=True)

    patronymic = models.CharField(
        _("CSCUser|patronymic"),
        max_length=100,
        blank=True)
    photo = ImageField(
        _("CSCUser|photo"),
        upload_to="photos/",
        blank=True)
    cropbox_data = JSONField(
        blank=True,
        null=True
    )
    note = models.TextField(
        _("CSCUser|note"),
        help_text=_("LaTeX+Markdown is enabled"),
        blank=True)
    enrollment_year = models.PositiveSmallIntegerField(
        _("CSCUser|enrollment year"),
        validators=[MinValueValidator(1990)],
        blank=True,
        null=True)
    graduation_year = models.PositiveSmallIntegerField(
        _("CSCUser|graduation year"),
        blank=True,
        validators=[MinValueValidator(1990)],
        null=True)
    curriculum_year = models.PositiveSmallIntegerField(
        _("CSCUser|Curriculum year"),
        validators=[MinValueValidator(2000)],
        blank=True,
        null=True)
    city = models.ForeignKey(City, verbose_name=_("Default city"),
                             help_text=_("CSCUser|city"),
                             blank=True, null=True,
                             on_delete=models.SET_NULL)
    # FIXME: why not null? The same for github_id
    yandex_id = models.CharField(
        _("Yandex ID"),
        max_length=80,
        validators=[RegexValidator(regex="^[^@]*$",
                                   message=_("Only the part before "
                                             "\"@yandex.ru\" is expected"))],
        blank=True)
    github_id = models.CharField(
        _("Github ID"),
        max_length=80,
        validators=[GITHUB_ID_VALIDATOR],
        blank=True)
    stepic_id = models.PositiveIntegerField(
        _("stepik.org ID"),
        blank=True,
        null=True)
    csc_review = models.TextField(
        _("CSC review"),
        help_text=_("LaTeX+Markdown is enabled"),
        blank=True)
    private_contacts = models.TextField(
        _("Contact information"),
        help_text=("{}; {}"
                   .format(_("LaTeX+Markdown is enabled"),
                           _("will be shown only to logged-in users"))),
        blank=True)
    # internal student info
    university = models.CharField(
        _("University"),
        max_length=255,
        blank=True)
    phone = models.CharField(
        _("Phone"),
        max_length=40,
        blank=True)
    uni_year_at_enrollment = models.CharField(
        _("StudentInfo|University year"),
        choices=COURSES,
        max_length=2,
        help_text=_("at enrollment"),
        null=True,
        blank=True)
    comment = models.TextField(
        _("Comment"),
        help_text=LATEX_MARKDOWN_ENABLED,
        blank=True)
    comment_changed_at = MonitorField(
        monitor='comment',
        verbose_name=_("Comment changed"))
    comment_last_author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Author of last edit"),
        on_delete=models.PROTECT,
        related_name='cscuser_commented',
        blank=True,
        null=True)
    status = models.CharField(
        choices=STATUS,
        verbose_name=_("Status"),
        help_text=_("Status|HelpText"),
        max_length=15,
        blank=True)
    status_last_change = MonitorStatusField(
        CSCUserStatusLog,
        verbose_name=_("Status changed"),
        blank=True,
        null=True,
        editable=False,
        monitored='status',
        logging_model=CSCUserStatusLog,
        on_delete=models.CASCADE)

    areas_of_study = models.ManyToManyField(
        'learning.AreaOfStudy',
        verbose_name=_("StudentInfo|Areas of study"),
        blank=True)
    workplace = models.CharField(
        _("Workplace"),
        max_length=200,
        blank=True)
    index_redirect = models.CharField(
        _("Index Redirect Option"),
        max_length=200,
        choices=PublicRoute.choices(),
        blank=True)

    objects = CustomUserManager()

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = _("CSCUser|user")
        verbose_name_plural = _("CSCUser|users")

    def clean(self):
        self.csc_review = self.csc_review.strip()

    def save(self, **kwargs):
        if self.email and not self.yandex_id:
            username, domain = self.email.split("@", 1)
            if domain in YANDEX_DOMAINS:
                self.yandex_id = username
        super(CSCUser, self).save(**kwargs)

    @property
    def city_code(self):
        city_code = getattr(self, "city_id", None)
        return city_code if city_code else None

    @staticmethod
    def create_student_from_applicant(applicant):
        """
        Create new model or override existent with data from applicant form.
        """
        from learning.admission.models import Applicant
        try:
            user = CSCUser.objects.get(email=applicant.email)
        except CSCUser.DoesNotExist:
            username = applicant.email.split("@", maxsplit=1)[0]
            if CSCUser.objects.filter(username=username).exists():
                username = CSCUser.generate_random_username(attempts=5)
            if not username:
                raise RuntimeError(
                    "Всё плохо. Имя {} уже занято. Cлучайное имя сгенерировать "
                    "не удалось".format(username))
            random_password = CSCUser.objects.make_random_password()
            user = CSCUser.objects.create_user(username=username,
                                               email=applicant.email,
                                               password=random_password)
        groups = []
        if applicant.status == Applicant.VOLUNTEER:
            groups.append(CSCUser.group.VOLUNTEER)
        else:
            groups.append(CSCUser.group.STUDENT_CENTER)
        user.groups.add(*groups)
        # Migrate data from application form to user profile
        same_attrs = [
            "first_name",
            "patronymic",
            "stepic_id",
            "phone"
        ]
        for attr_name in same_attrs:
            setattr(user, attr_name, getattr(applicant, attr_name))
        user.last_name = applicant.surname
        user.enrollment_year = user.curriculum_year = timezone.now().year
        # Looks like the same fields below
        user.yandex_id = applicant.yandex_id if applicant.yandex_id else ""
        # For github store part after github.com/
        if applicant.github_id:
            user.github_id = applicant.github_id.split("github.com/",
                                                       maxsplit=1)[-1]
        user.workplace = applicant.workplace if applicant.workplace else ""
        user.uni_year_at_enrollment = applicant.course
        user.city_id = applicant.campaign.city_id
        user.university = applicant.university.name
        user.save()
        return user

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
            CSCUser.objects.get(username=username)
            return CSCUser.generate_random_username(
                length=length, chars=chars, split=split, delimiter=delimiter,
                attempts=attempts - 1)
        except CSCUser.DoesNotExist:
            return username

    def __str__(self):
        return smart_text(self.get_full_name(True))

    def get_absolute_url(self):
        return reverse('user_detail', args=[self.pk])

    def get_classes_icalendar_url(self):
        # Returns relative path
        return reverse('user_ical_classes', args=[self.pk])

    def get_assignments_icalendar_url(self):
        return reverse('user_ical_assignments', args=[self.pk])

    def teacher_profile_url(self):
        return reverse('teacher_detail', args=[self.pk])

    def get_applicant_form_url(self):
        try:
            applicant_form_url = reverse("admission:applicant_detail",
                                         args=[self.applicant.pk])
        except ObjectDoesNotExist:
            applicant_form_url = None
        return applicant_form_url

    def get_full_name(self, last_name_first=False):
        if last_name_first:
            parts = [self.last_name, self.first_name, self.patronymic]
        else:
            parts = [self.first_name, self.patronymic, self.last_name]
        full_name = smart_text(" "
                               .join(part for part in parts if part)
                               .strip())
        return full_name or self.username

    def get_short_name(self):
        return (smart_text(" ".join([self.first_name, self.last_name]).strip())
                or self.username)

    def get_abbreviated_short_name(self, last_name_first=True):
        first_letter = self.first_name[:1] + "." if self.first_name else ""
        if last_name_first:
            parts = [self.last_name, first_letter]
        else:
            parts = [first_letter, self.last_name]
        return " ".join(parts).strip() or self.username

    def get_abbreviated_name(self):
        parts = [self.first_name[:1], self.patronymic[:1], self.last_name]
        abbrev_name = smart_text(". ".join(p for p in parts if p).strip())
        return abbrev_name or self.username

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
        return ".".join(parts).translate(en_to_ru_mapping)

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

    def photo_thumbnail_cropbox(self):
        """Used by `thumbnail` template tag. Format: x1,y1,x2,y2"""
        if self.cropbox_data:
            return photo_thumbnail_cropbox(self.cropbox_data)
        return ""

    def get_thumbnail(self, geometry, use_stub=True, **options):
        path_to_img = getattr(self, "photo", None)
        # Default crop settings
        if "crop" not in options:
            options["crop"] = "center top"
        if "cropbox" not in options:
            options["cropbox"] = self.photo_thumbnail_cropbox()
        thumbnail = get_thumbnail(path_to_img, geometry, **options)
        if not thumbnail or isinstance(thumbnail, DummyImageFile):
            if use_stub:
                if not self.is_teacher and self.gender == CSCUser.GENDER_MALE:
                    factory = BoyStubImage
                elif not self.is_teacher and self.gender == CSCUser.GENDER_FEMALE:
                    factory = GirlStubImage
                else:
                    factory = BaseStubImage
                thumbnail = factory(geometry=geometry)
            else:
                thumbnail = None
        return thumbnail

    # FIXME(Dmitry): this should use model_utils.fields#SplitField
    def get_short_note(self):
        """Returns only the first paragraph from the note."""
        normalized_note = normalize_newlines(self.note)
        lf = normalized_note.find("\n")
        return self.note if lf == -1 else normalized_note[:lf]

    # TODO: think how to add declension method with ru/en support

    @cached_property
    def _cached_groups(self):
        try:
            gs = self._prefetched_objects_cache['groups']
            user_groups = set(g.pk for g in gs)
        except (AttributeError, KeyError):
            user_groups = set(self.groups.values_list("pk", flat=True))
        # Add club group on club site to center students
        center_student = (self.group.STUDENT_CENTER in user_groups or
                          self.group.VOLUNTEER in user_groups or
                          self.group.GRADUATE_CENTER in user_groups)
        if (center_student and self.group.STUDENT_CLUB not in user_groups
                and is_club_site()):
            user_groups.add(self.group.STUDENT_CLUB)
        return user_groups

    def enrollment_in_the_course(self, course_offering_id) -> Optional[Enrollment]:
        enrollment_qs = Enrollment.active.filter(
            student=self, course_offering_id=course_offering_id)
        if self.is_student or self.is_graduate:
            return enrollment_qs.first()
        return None

    # TODO: move to Project manager?
    def get_projects_queryset(self):
        """Returns projects through ProjectStudent intermediate model"""
        return (self.projectstudent_set
                .select_related('project', 'project__semester')
                .order_by('project__semester__index'))

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
        if self.is_student:
            sections.append(PublicRoute.LEARNING.choice)
        if self.is_teacher:
            sections.append(PublicRoute.TEACHING.choice)
        if self.is_curator:
            sections.append(PublicRoute.STAFF.choice)
        return sections

    def stats(self, current_term):
        """
        Stats for SUCCESSFULLY completed courses and enrollments in 
        requested term.
        Additional DB queries may occur:
            * enrollment_set
            * enrollment_set__course_offering (for each enrollment)
            * enrollment_set__course_offering__courseclasses (for each course)
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
        # FIXME: add test for `is_deleted=False`. Check all incomings for `enrollment_set`
        for e in self.enrollment_set.filter(is_deleted=False).all():
            in_current_term = e.course_offering.semester_id == current_term.pk
            if in_current_term:
                in_current_term_total += 1
                in_current_term_courses.add(e.course_offering.course_id)
            if e.course_offering.is_open:
                # See queryset in `cast_students_to_will_graduate`
                if hasattr(e, "classes_total"):
                    classes_total = e.classes_total
                else:
                    classes_total = (e.course_offering.courseclass_set.count())
                contribution = 0.5 if classes_total < 6 else 1
                if is_positive_grade(e.grade):
                    club_courses.add(e.course_offering.course_id)
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
                if is_positive_grade(e.grade):
                    center_courses.add(e.course_offering.course_id)
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
            if is_positive_grade(c.grade):
                shad_total += 1
            if c.semester_id == current_term.pk:
                in_current_term_total += 1
                if is_negative_grade(c.grade):
                    failed_total += 1
            # `not graded` == failed for passed terms
            elif not is_positive_grade(c.grade):
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
            "in_term": {
                "total": in_current_term_total,
                "courses": in_current_term_courses,  # center and club courses
                "passed": in_current_term_passed,  # center and club
                "failed": in_current_term_failed,  # center and club
                # FIXME: adusted value, not int
                "in_progress": in_current_term_in_progress,
            }
        }


@python_2_unicode_compatible
class OnlineCourseRecord(TimeStampedModel):
    student = models.ForeignKey(
        CSCUser,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)
    name = models.CharField(_("Course|name"), max_length=255)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Online course record")
        verbose_name_plural = _("Online course records")

    def __str__(self):
        return smart_text(self.name)


@python_2_unicode_compatible
class SHADCourseRecord(TimeStampedModel):
    GRADES = GRADES
    student = models.ForeignKey(
        CSCUser,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)
    name = models.CharField(_("Course|name"), max_length=255)
    teachers = models.CharField(_("Teachers"), max_length=255)
    semester = models.ForeignKey(
        'learning.Semester',
        verbose_name=_("Semester"),
        on_delete=models.PROTECT)

    grade = StatusField(
        verbose_name=_("Enrollment|grade"),
        choices_name='GRADES',
        default='not_graded')

    class Meta:
        ordering = ["name"]
        verbose_name = _("SHAD course record")
        verbose_name_plural = _("SHAD course records")

    @property
    def grade_display(self):
        return GRADES[self.grade]

    def __str__(self):
        return smart_text("{} [{}]".format(self.name, self.student_id))


@python_2_unicode_compatible
class CSCUserReference(TimeStampedModel):
    signature = models.CharField(_("Reference|signature"), max_length=255)
    note = models.TextField(_("Reference|note"), blank=True)

    student = models.ForeignKey(
        CSCUser,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)

    class Meta:
        ordering = ["signature"]
        verbose_name = _("User reference record")
        verbose_name_plural = _("User reference records")

    def __str__(self):
        return smart_text(self.student)


class NotAuthenticatedUser(LearningPermissionsMixin, AnonymousUser):
    group = PARTICIPANT_GROUPS
    city_code = None
    index_redirect = None

    def __str__(self):
        return 'NotAuthenticatedUser'

    def enrollment_in_the_course(self, course_offering_id: int) -> Optional[Enrollment]:
        return None
