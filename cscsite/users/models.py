from __future__ import unicode_literals, absolute_import

import logging

import datetime
import django_filters
from django.conf import settings
from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Count, Case, F, When, Value, Q
from django.http import QueryDict
from django.utils.encoding import smart_text, python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.text import normalize_newlines
from django.utils.timezone import now, make_aware
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from model_utils.fields import MonitorField, StatusField, AutoLastModifiedField
from model_utils.models import TimeStampedModel
from sorl.thumbnail import ImageField

from core.models import LATEX_MARKDOWN_ENABLED
from learning.settings import PARTICIPANT_GROUPS, STUDENT_STATUS, GRADES
from learning.models import Enrollment
from learning.utils import LearningPermissionsMixin
from .managers import CustomUserManager

# See 'https://help.yandex.ru/pdd/additional/mailbox-alias.xml'.
YANDEX_DOMAINS = ["yandex.ru", "narod.ru", "yandex.ua",
                  "yandex.by", "yandex.kz", "ya.ru", "yandex.com"]


logger = logging.getLogger(__name__)

# TODO: Add tests
class MonitorFieldMixin(object):
    def __init__(self, *args, **kwargs):
        log_class = kwargs.pop('log_class', None)
        if not log_class:
            raise TypeError(
                '%s requires a "log_class" argument' % self.__class__.__name__)
        self.log_class = log_class
        # TODO: Check methods get_default_value and _prepare_blabla. raise exceptions
        monitor = kwargs.pop('monitor', None)
        if not monitor:
            raise TypeError(
                '%s requires a "monitor" argument' % self.__class__.__name__)
        self.monitor = monitor
        kwargs.setdefault('help_text', _("Automatically updated when {} "
                                         "changed, but you still can set "
                                         "it manually. Make no sense without "
                                         "{} update").format(monitor, monitor))
        when = kwargs.pop('when', None)
        if when is not None:
            when = set(when)
        self.when = when
        super(MonitorFieldMixin, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        self.old_value_attname = '_old_value_%s' % name
        self.monitor_attname = '_monitor_%s' % name
        models.signals.post_init.connect(self._save_initial, sender=cls)
        models.signals.post_save.connect(self._post_save, sender=cls)
        super(MonitorFieldMixin, self).contribute_to_class(cls, name, **kwargs)

    def get_monitored_value(self, instance):
        return getattr(instance, self.monitor)

    def _save_initial(self, sender, instance, **kwargs):
        setattr(instance, self.old_value_attname,
                getattr(instance, self.attname))
        setattr(instance, self.monitor_attname,
                self.get_monitored_value(instance))

    def _post_save(self, instance, created, **kwargs):
        previous = getattr(instance, self.monitor_attname, None)
        current = self.get_monitored_value(instance)
        if previous != current:
            self._save_initial(instance.__class__, instance)
            # TODO: empty attname value here instead of log_class
            self.create_log_entry(instance, created)

    def create_log_entry(self, instance, created):
        if created:
            return False
        attrs = {}
        attrs[self.monitor] = self.get_monitored_value(instance)
        instance_fields = [f.attname for f in instance._meta.fields]
        for field in self.log_class._meta.fields:
            if isinstance(field, models.AutoField):
                continue
            if field.attname not in instance_fields:
                continue
            attrs[field.attname] = getattr(instance, field.attname)

        model = self.log_class(**attrs)
        if model._prepare_fields(instance, self.attname):
            model.save()

    def deconstruct(self):
        name, path, args, kwargs = super(MonitorFieldMixin, self).deconstruct()
        kwargs['monitor'] = self.monitor
        kwargs['log_class'] = self.log_class
        if self.when is not None:
            kwargs['when'] = self.when
        return name, path, args, kwargs


# TODO: mv to db/ package. Should be more generic?
class MonitorDateField(MonitorFieldMixin, models.DateField):
    """ MonitorField from django.utils + added logging
    Also you can manually set date if required

    """

    def pre_save(self, model_instance, add):
        value = now()
        attname_previous = getattr(model_instance, self.old_value_attname, None)
        attname_current = getattr(model_instance, self.attname)
        previous = getattr(model_instance, self.monitor_attname, None)
        current = self.get_monitored_value(model_instance)
        if previous != current and (
                attname_previous == attname_current or not attname_current):
            if self.when is None or current in self.when:
                setattr(model_instance, self.attname, value)
        return super(MonitorDateField, self).pre_save(model_instance, add)


class MonitorFKField(MonitorFieldMixin, models.ForeignKey):
    def pre_save(self, model_instance, add):
        value = self.log_class.get_default_value()
        attname_current_value = getattr(model_instance, self.attname)
        previous = getattr(model_instance, self.monitor_attname, None)
        current = self.get_monitored_value(model_instance)
        if previous != current and not attname_current_value:
            if self.when is None or current in self.when:
                setattr(model_instance, self.attname, value)
        return super(MonitorFKField, self).pre_save(model_instance, add)


@python_2_unicode_compatible
class CSCUserStatusLog(models.Model):
    created = models.DateField(_("created"), default=now)
    semester = models.ForeignKey(
        "learning.Semester",
        verbose_name=_("Semester"))
    status = models.CharField(
        choices=STUDENT_STATUS,
        verbose_name=_("Status"),
        max_length=15)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Student"))

    @staticmethod
    def get_default_value():
        from learning.models import Semester
        semester = Semester.get_current()
        return semester.pk

    def _prepare_fields(self, monitored_instance, observer_field_attname):
        if not self.student_id:
            self.student_id = monitored_instance.pk
        if not self.semester_id:
            semester_id = getattr(monitored_instance, observer_field_attname,
                                  None)
            if not semester_id:
                self.semester_id = self.get_default_value()
            else:
                self.semester_id = semester_id
                # checkmate, we null FK reference here. now :<
                setattr(monitored_instance, observer_field_attname, None)
                monitored_instance.save()
        return True

    def __str__(self):
        return smart_text(
            "{} [{}]".format(self.student.get_full_name(True), self.semester))


@python_2_unicode_compatible
class CSCUser(LearningPermissionsMixin, AbstractUser):

    # FIXME: replace `groups__name` with groups__pk in learning.signals
    group_pks = PARTICIPANT_GROUPS

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

    _original_comment = None

    modified = AutoLastModifiedField(_('modified'))

    patronymic = models.CharField(
        _("CSCUser|patronymic"),
        max_length=100,
        blank=True)
    photo = ImageField(
        _("CSCUser|photo"),
        upload_to="photos/",
        blank=True)
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
        validators=[RegexValidator(
            regex="^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]$")],
        blank=True)
    stepic_id = models.PositiveIntegerField(
        _("Stepic ID"),
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
        max_length=15,
        blank=True)

    status_changed_at = MonitorFKField(
        "learning.Semester",
        verbose_name=_("Status changed"),
        blank=True,
        null=True,
        monitor='status',
        log_class=CSCUserStatusLog)

    study_programs = models.ManyToManyField(
        'learning.StudyProgram',
        verbose_name=_("StudentInfo|Study programs"),
        blank=True)
    workplace = models.CharField(
        _("Workplace"),
        max_length=200,
        blank=True)

    objects = CustomUserManager()

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = _("CSCUser|user")
        verbose_name_plural = _("CSCUser|users")

    def __init__(self, *args, **kwargs):
        super(CSCUser, self).__init__(*args, **kwargs)
        self._original_comment = self.comment

    def save(self, **kwargs):
        if self.email and not self.yandex_id:
            username, domain = self.email.split("@", 1)
            if domain in YANDEX_DOMAINS:
                self.yandex_id = username

        if self.comment != self._original_comment:
            author = kwargs.get('edit_author')
            if author is None:
                logger.warning("edit_author is not provided, kwargs {}"
                               .format(kwargs))
            else:
                self.comment_last_author = author
        if 'edit_author' in kwargs:
            del kwargs['edit_author']

        super(CSCUser, self).save(**kwargs)
        self._original_comment = self.comment

    def __str__(self):
        return smart_text(self.get_full_name(True))

    def get_absolute_url(self):
        return reverse('user_detail', args=[self.pk])

    def teacher_profile_url(self):
        return reverse('teacher_detail', args=[self.pk])

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
        return (smart_text(" ".join([self.last_name,
                                     self.first_name]).strip())
                or self.username)

    def get_abbreviated_name(self):
        parts = [self.first_name[:1], self.patronymic[:1], self.last_name]
        sign = "."
        # By the decree of Alexander, added additional whitespace for club site
        if settings.SITE_ID == 2:
            sign += " "
        abbrev_name = smart_text(str(sign)
                                 .join(part for part in parts if part)
                                 .strip())
        return abbrev_name or self.username

    # FIXME(Dmitry): this should use model_utils.fields#SplitField
    def get_short_note(self):
        """Returns only the first paragraph from the note."""
        normalized_note = normalize_newlines(self.note)
        lf = normalized_note.find("\n")
        return self.note if lf == -1 else normalized_note[:lf]

    @cached_property
    def _cs_group_pks(self):
        try:
            user_groups = self._prefetched_objects_cache['groups']
            user_groups = [group.pk for group in user_groups]
        except (AttributeError, KeyError):
            user_groups = self.groups.values_list("pk", flat=True).all()
        # Remove student center group if user expelled
        if self.status == self.STATUS.expelled:
            user_groups = [pk for pk in user_groups
                           if pk != self.group_pks.STUDENT_CENTER]
        return user_groups

    @property
    def status_display(self):
        if self.status in self.STATUS:
            return self.STATUS[self.status]
        else:
            return ''

    @property
    def uni_year_at_enrollment_display(self):
        if self.uni_year_at_enrollment in self.COURSES:
            return self.COURSES[self.uni_year_at_enrollment]
        else:
            return ''

    @property
    def is_student(self):
        return self.is_student_center or \
               self.is_student_club or \
               self.is_volunteer

    @cached_property
    def is_student_center(self):
        return self.group_pks.STUDENT_CENTER in self._cs_group_pks

    @cached_property
    def is_student_club(self):
        return self.group_pks.STUDENT_CLUB in self._cs_group_pks

    @cached_property
    def is_teacher(self):
        return self.group_pks.TEACHER_CENTER in self._cs_group_pks or \
               self.group_pks.TEACHER_CLUB in self._cs_group_pks

    @cached_property
    def is_graduate(self):
        return self.group_pks.GRADUATE_CENTER in self._cs_group_pks

    @cached_property
    def is_volunteer(self):
        return self.group_pks.VOLUNTEER in self._cs_group_pks

    @cached_property
    def is_curator(self):
        return self.is_superuser and self.is_staff


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


class ListFilter(django_filters.Filter):
    """key=value1,value2,value3 filter for django_filters"""
    def filter(self, qs, value):
        value_list = value.split(u',')
        value_list = filter(None, value_list)
        return super(ListFilter, self).filter(qs, django_filters.fields.Lookup(
            value_list, 'in'))


class CSCUserFilter(django_filters.FilterSet):
    FILTERING_GROUPS = [CSCUser.group_pks.VOLUNTEER,
                        CSCUser.group_pks.STUDENT_CENTER,
                        CSCUser.group_pks.GRADUATE_CENTER]

    ENROLLMENTS_CNT_LIMIT = 12

    _lexeme_trans_map = dict((ord(c), None) for c in '*|&:')

    name = django_filters.MethodFilter(action='name_filter')
    cnt_enrollments = django_filters.MethodFilter(action='cnt_enrollments_filter')
    # FIXME: replace with range?
    enrollment_year = ListFilter(name='enrollment_year')
    status = django_filters.MethodFilter(action='status_filter')

    class Meta:
        model = CSCUser
        fields = ["name", "enrollment_year", "groups", "status", "cnt_enrollments"]

    def __init__(self, *args, **kwargs):
        self.empty_query = False
        super(CSCUserFilter, self).__init__(*args, **kwargs)
        # Remove empty values
        cleaned_data = QueryDict(mutable=True)
        if self.data:
            for (filter_name, filter_values) in self.data.iterlists():
                values = filter(None, filter_values)
                if values:
                    cleaned_data.setlist(filter_name, set(values))
        self.data = cleaned_data
        if not "groups" in self.data:
            if not self.data:
                self.empty_query = True
            self.data.setlist("groups", self.FILTERING_GROUPS)

    def cnt_enrollments_filter(self, queryset, value):
        try:
            value = int(value)
        except ValueError:
            return queryset
        assert value >= 0

        queryset = queryset.annotate(
            courses_cnt=
            Count(Case(
                When(Q(enrollment__grade=Enrollment.GRADES.not_graded) | Q(
                    enrollment__grade=Enrollment.GRADES.unsatisfactory),
                     then=Value(None)),
                default=F("enrollment")
            ), distinct=True)
            + Count("shadcourserecord", distinct=True)
            + Count("onlinecourserecord", distinct=True)
        )

        if value > self.ENROLLMENTS_CNT_LIMIT:
            return queryset.filter(
                courses_cnt__gt=self.ENROLLMENTS_CNT_LIMIT)
        else:
            return queryset.filter(courses_cnt=value)

    def status_filter(self, queryset, value):
        value_list = value.split(u',')
        value_list = filter(None, value_list)
        if "studying" in value_list and CSCUser.STATUS.expelled in value_list:
            return queryset
        elif "studying" in value_list:
            return queryset.exclude(status=CSCUser.STATUS.expelled)
        for value in value_list:
            if value not in CSCUser.STATUS:
                raise ValueError(
                    "CSCUserFilter: unrecognized status_filter choice")
        return queryset.filter(status__in=value_list).distinct()


    # FIXME: Difficult and unpredictable
    def name_filter(self, queryset, value):
        qstr = value.strip()
        tsquery = self._form_name_tsquery(qstr)
        if tsquery is None:
            return queryset
        else:
            return (queryset
                    .extra(where=["to_tsvector(first_name || ' ' || last_name) "
                                  "@@ to_tsquery(%s)"],
                           params=[tsquery])
                    .exclude(first_name__exact='',
                             last_name__exact=''))

    def _form_name_tsquery(self, qstr):
        if qstr is None or not (2 < len(qstr) < 100):
            return
        lexems = []
        for s in qstr.split(' '):
            lexeme = s.translate(self._lexeme_trans_map).strip()
            if len(lexeme) > 0:
                lexems.append(lexeme)
        if len(lexems) > 3:
            return
        return " & ".join("{}:*".format(l) for l in lexems)


class NotAuthenticatedUser(LearningPermissionsMixin, AnonymousUser):
    pass
