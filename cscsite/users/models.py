import base64
import logging
from random import choice
from string import ascii_lowercase, digits
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import smart_text
from django.utils.functional import cached_property
from django.utils.text import normalize_newlines
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField
from model_utils.fields import MonitorField, AutoLastModifiedField
from model_utils.models import TimeStampedModel
from sorl.thumbnail import ImageField, get_thumbnail
from sorl.thumbnail.images import DummyImageFile

from ajaxuploader.utils import photo_thumbnail_cropbox
from core.models import LATEX_MARKDOWN_ENABLED, City
from core.utils import is_club_site, en_to_ru_mapping
from cscenter.utils import PublicRoute
from learning.models import Semester, Enrollment
from learning.permissions import LearningPermissionsMixin
from learning.settings import AcademicDegreeYears, AcademicRoles, \
    StudentStatuses, GradeTypes
from learning.utils import is_negative_grade
from users.settings import GROUPS_IMPORT_TO_GERRIT
from users.tasks import update_password_in_gerrit
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
    Logging changes of another model field, stores link to the last change.
    Reset monitoring field value by log cls after log entry was added to DB.

    Args:
        logging_model (cls):
            Model responsible for logging.
        monitored (string):
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
        self._monitored_attrname = '_monitored_%s' % name
        models.signals.post_init.connect(self._save_initial, sender=cls)
        super().contribute_to_class(cls, name, **kwargs)

    def _save_initial(self, sender, instance, **kwargs):
        if self.monitored in instance.get_deferred_fields():
            return
        setattr(instance, self._monitored_attrname,
                self.get_monitored_value(instance))

    def get_monitored_value(self, instance):
        return getattr(instance, self.monitored)

    def pre_save(self, model_instance, add):
        monitored_prev = getattr(model_instance, self._monitored_attrname)
        monitored_current = self.get_monitored_value(model_instance)
        if monitored_prev != monitored_current:
            if self.when is None or monitored_current in self.when:
                log_model = self.create_log_entry(model_instance, add)
                setattr(model_instance, self.attname, log_model.pk)
                self._save_initial(model_instance.__class__, model_instance)
        return super().pre_save(model_instance, add)

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


class UserStatusLog(models.Model):
    created = models.DateField(_("created"), default=now)
    semester = models.ForeignKey(
        "learning.Semester",
        verbose_name=_("Semester"),
        on_delete=models.CASCADE)
    status = models.CharField(
        choices=StudentStatuses.choices,
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
        return smart_text("{} [{}]".format(
            self.student.get_full_name(True), self.semester))


class User(LearningPermissionsMixin, AbstractUser):

    roles = AcademicRoles

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
        choices=AcademicDegreeYears.choices,
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
        related_name='user_commented',
        blank=True,
        null=True)
    status = models.CharField(
        choices=StudentStatuses.choices,
        verbose_name=_("Status"),
        help_text=_("Status|HelpText"),
        max_length=15,
        blank=True)
    status_last_change = MonitorStatusField(
        UserStatusLog,
        verbose_name=_("Status changed"),
        blank=True,
        null=True,
        editable=False,
        monitored='status',
        logging_model=UserStatusLog,
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
        db_table = 'users_user'
        ordering = ['last_name', 'first_name']
        verbose_name = _("CSCUser|user")
        verbose_name_plural = _("CSCUser|users")

    def clean(self):
        self.csc_review = self.csc_review.strip()

    def save(self, **kwargs):
        created = self.pk is None
        password_changed = self._password is not None
        if self.email and not self.yandex_id:
            username, domain = self.email.split("@", 1)
            if domain in YANDEX_DOMAINS:
                self.yandex_id = username
        super().save(**kwargs)
        # Schedules redis queue task to update user password in gerrit's
        # LDAP database if password was changed.
        gerrit_sync_enabled = getattr(settings, "LDAP_SYNC_PASSWORD", False)
        if not created and password_changed and gerrit_sync_enabled:
            if self.get_cached_groups().intersection(GROUPS_IMPORT_TO_GERRIT):
                update_password_in_gerrit.delay(user_id=self.pk)
        elif created and gerrit_sync_enabled:
            # TODO: schedule task for creating LDAP account
            pass

    @property
    def city_code(self):
        city_code = getattr(self, "city_id", None)
        return city_code if city_code else None

    @property
    def is_expelled(self):
        return self.status == StudentStatuses.EXPELLED

    @staticmethod
    def create_student_from_applicant(applicant):
        """
        Create new model or override existent with data from applicant form.
        """
        from admission.models import Applicant
        try:
            user = User.objects.get(email=applicant.email)
        except User.DoesNotExist:
            username = applicant.email.split("@", maxsplit=1)[0]
            if User.objects.filter(username=username).exists():
                username = User.generate_random_username(attempts=5)
            if not username:
                raise RuntimeError(
                    "Всё плохо. Имя {} уже занято. Cлучайное имя сгенерировать "
                    "не удалось".format(username))
            random_password = User.objects.make_random_password()
            user = User.objects.create_user(username=username,
                                            email=applicant.email,
                                            password=random_password)
        groups = []
        if applicant.status == Applicant.VOLUNTEER:
            groups.append(User.roles.VOLUNTEER)
        else:
            groups.append(User.roles.STUDENT_CENTER)
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
            User.objects.get(username=username)
            return User.generate_random_username(
                length=length, chars=chars, split=split, delimiter=delimiter,
                attempts=attempts - 1)
        except User.DoesNotExist:
            return username

    @property
    def password_hash_ldap(self) -> Optional[bytes]:
        """
        Converts Django's password hash representation to LDAP compatible
        hasher format. Supports pbkdf2 hasher only.
        """
        algorithm, iterations, salt, hash = self.password.split('$', 3)
        if algorithm == "pbkdf2_sha256":
            ldap_hasher_code = "{PBKDF2-SHA256}"
        elif algorithm == "pbkdf2_sha512":
            ldap_hasher_code = "{PBKDF2-SHA512}"
        elif algorithm == "pbkdf2_sha1":
            ldap_hasher_code = "{PBKDF2-SHA1}"
        else:
            return None
        # Works like `passlib.utils.binary.ab64_encode` except
        # converting "+" to "."
        ab64_salt = base64.b64encode(salt.encode("utf-8")).rstrip(b"=\n")
        h = f"{ldap_hasher_code}{iterations}${ab64_salt.decode('utf-8')}${hash}"
        return h.encode("utf-8")

    @property
    def ldap_username(self):
        """
        Portable Filename Character Set (according to POSIX.1-2017) is used for
        username since @ in username can be misleading when you connected
        over ssh. `foo@localhost.ru@domain.ltd` really looks weird.
        """
        return self.email.replace("@", ".")

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
                if not self.is_teacher and self.gender == User.GENDER_MALE:
                    factory = BoyStubImage
                elif not self.is_teacher and self.gender == User.GENDER_FEMALE:
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
    def _cached_groups(self) -> set:
        try:
            gs = self._prefetched_objects_cache['groups']
            user_groups = set(g.pk for g in gs)
        except (AttributeError, KeyError):
            user_groups = set(self.groups.values_list("pk", flat=True))
        # Add club group on club site to center students
        center_student = (self.roles.STUDENT_CENTER in user_groups or
                          self.roles.VOLUNTEER in user_groups or
                          self.roles.GRADUATE_CENTER in user_groups)
        if (center_student and self.roles.STUDENT_CLUB not in user_groups
                and is_club_site()):
            user_groups.add(self.roles.STUDENT_CLUB)
        return user_groups

    def get_enrollment(self, course_id: int) -> Optional[Enrollment]:
        """
        Query enrollment from db on first call and cache the result. Cache
        won't be refreshed if enrollment was deleted or changed after call.
        """
        if self.is_student or self.is_graduate:
            cache_key = f"_student_enrollment_{course_id}"
            if not hasattr(self, cache_key):
                e = (Enrollment.active
                     .filter(student=self,
                             course_id=course_id)
                     .order_by()
                     .first())
                setattr(self, cache_key, e)
            return getattr(self, cache_key)
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
        # FIXME: add test for `is_deleted=False`. Check all incomings for `enrollment_set`
        for e in self.enrollment_set.filter(is_deleted=False).all():
            in_current_term = e.course.semester_id == current_term.pk
            if in_current_term:
                in_current_term_total += 1
                in_current_term_courses.add(e.course.meta_course_id)
            if e.course.is_open:
                # See queryset in `cast_students_to_will_graduate`
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
            if c.semester_id == current_term.pk:
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
            "in_term": {
                "total": in_current_term_total,
                "courses": in_current_term_courses,  # center and club courses
                "passed": in_current_term_passed,  # center and club
                "failed": in_current_term_failed,  # center and club
                # FIXME: adusted value, not int
                "in_progress": in_current_term_in_progress,
            }
        }


class OnlineCourseRecord(TimeStampedModel):
    student = models.ForeignKey(
        User,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)
    name = models.CharField(_("Course|name"), max_length=255)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Online course record")
        verbose_name_plural = _("Online course records")

    def __str__(self):
        return smart_text(self.name)


class SHADCourseRecord(TimeStampedModel):
    GRADES = GradeTypes
    student = models.ForeignKey(
        User,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)
    name = models.CharField(_("Course|name"), max_length=255)
    teachers = models.CharField(_("Teachers"), max_length=255)
    semester = models.ForeignKey(
        'learning.Semester',
        verbose_name=_("Semester"),
        on_delete=models.PROTECT)

    grade = models.CharField(
        max_length=100,
        verbose_name=_("Enrollment|grade"),
        choices=GradeTypes.choices,
        default=GradeTypes.NOT_GRADED)

    class Meta:
        ordering = ["name"]
        verbose_name = _("SHAD course record")
        verbose_name_plural = _("SHAD course records")

    @property
    def grade_display(self):
        return self.GRADES.values[self.grade]

    def __str__(self):
        return smart_text("{} [{}]".format(self.name, self.student_id))


# TODO: move to learning app?
class EnrollmentCertificate(TimeStampedModel):
    signature = models.CharField(_("Reference|signature"), max_length=255)
    note = models.TextField(_("Reference|note"), blank=True)

    student = models.ForeignKey(
        User,
        verbose_name=_("Student"),
        on_delete=models.CASCADE,
        related_name="enrollment_certificates")

    class Meta:
        ordering = ["signature"]
        verbose_name = _("User reference record")
        verbose_name_plural = _("User reference records")

    def __str__(self):
        return smart_text(self.student)


class NotAuthenticatedUser(LearningPermissionsMixin, AnonymousUser):
    group = AcademicRoles
    city_code = None
    index_redirect = None

    def __str__(self):
        return 'NotAuthenticatedUser'

    def get_enrollment(self, course_id: int) -> Optional[Enrollment]:
        return None
