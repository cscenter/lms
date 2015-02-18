from __future__ import unicode_literals, absolute_import

import logging

from model_utils import Choices
from model_utils.fields import MonitorField
from model_utils.models import TimeStampedModel
from sorl.thumbnail import ImageField

from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator, \
    RegexValidator
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_text, python_2_unicode_compatible
from django.utils.text import normalize_newlines
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property

from core.models import LATEX_MARKDOWN_ENABLED

# See 'https://help.yandex.ru/pdd/additional/mailbox-alias.xml'.
YANDEX_DOMAINS = ["yandex.ru", "narod.ru", "yandex.ua",
                  "yandex.by", "yandex.kz", "ya.ru", "yandex.com"]


logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class CSCUser(AbstractUser):
    IS_STUDENT_PK = 1
    IS_TEACHER_PK = 2
    IS_GRADUATE_PK = 3

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

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = _("CSCUser|user")
        verbose_name_plural = _("CSCUser|users")

    def clean(self):
        # avoid checking if the model wasn't yet saved, otherwise exception
        # will be thrown about missing many-to-many relation
        if self.pk:
            if self.is_student and self.enrollment_year is None:
                raise ValidationError(_("CSCUser|enrollment year should be "
                                        "provided for students"))
            if self.is_graduate and self.graduation_year is None:
                raise ValidationError(_("CSCUser|graduation year should be "
                                        " provided for graduates"))

    def save(self, **kwargs):
        if self.email and not self.yandex_id:
            username, domain = self.email.split("@", 1)
            if domain in YANDEX_DOMAINS:
                self.yandex_id = username

        super(CSCUser, self).save(**kwargs)

    def __str__(self):
        return smart_text(self.get_full_name(True))

    def get_absolute_url(self):
        return reverse('user_detail', args=[self.pk])

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
        abbrev_name = smart_text("."
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
        return self.groups.values_list("pk", flat=True)

    @property
    def is_student(self):
        return self.IS_STUDENT_PK in self._cs_group_pks

    @property
    def is_teacher(self):
        return self.IS_TEACHER_PK in self._cs_group_pks

    @property
    def is_graduate(self):
        return self.IS_GRADUATE_PK in self._cs_group_pks


@python_2_unicode_compatible
class StudentInfo(TimeStampedModel):
    STUDY_PROGRAMS = Choices(('dm', _("Data mining")),
                             ('cs', _("Computer Science")),
                             ('se', _("Software Engineering")))
    STATUS = Choices(('graduate', _("Graduate")),
                     ('expelled', _("StudentInfo|Expelled")),
                     ('reinstated', _("StudentInfo|Reinstalled")),
                     ('will_graduate', _("StudentInfo|Will graduate")))

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)

    university = models.CharField(
        _("University"),
        max_length=140,
        blank=True)
    phone = models.CharField(
        _("Phone"),
        max_length=40,
        blank=True)
    uni_year_at_enrollment = models.PositiveSmallIntegerField(
        _("StudentInfo|University year"),
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text=_("at enrollment"),
        null=True,
        blank=True)
    comment = models.TextField(
        _("Comment"),
        help_text=LATEX_MARKDOWN_ENABLED,
        blank=True)
    comment_changed = MonitorField(
        monitor='comment',
        verbose_name=_("Comment changed"))
    comment_last_author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Author of last edit"),
        on_delete=models.PROTECT,
        related_name='studentinfo_commented')
    nondegree = models.BooleanField(
        _("Non-degree student"),
        default=False)
    status = models.CharField(
        choices=STATUS,
        verbose_name=_("Status"),
        max_length=15,
        blank=True)
    study_program = models.CharField(
        choices=STUDY_PROGRAMS,
        verbose_name=_("StudentInfo|Study program"),
        max_length=2,
        blank=True)
    online_courses = models.TextField(
        _("Online courses"),
        help_text=LATEX_MARKDOWN_ENABLED,
        blank=True)
    shad_courses = models.TextField(
        _("School of Data Analysis courses"),
        help_text=LATEX_MARKDOWN_ENABLED,
        blank=True)
    workplace = models.CharField(
        _("Workplace"),
        max_length=200,
        blank=True)

    class Meta:
        ordering = ["student"]
        verbose_name = _("Student info record")
        verbose_name_plural = _("Student info records")

    def __str__(self):
        return smart_text(self.student)

    # overrides

    _original_comment = None

    def __init__(self, *args, **kwargs):
        super(StudentInfo, self).__init__(*args, **kwargs)
        self._original_comment = self.comment

    def save(self, *args, **kwargs):
        author = kwargs.get('edit_author')
        if author is None:
            logger.warning("edit_author is not provided, kwargs {}"
                           .format(kwargs))
        else:
            del kwargs['edit_author']
        if self.comment != self._original_comment:
            self.comment_last_author = author
        super(StudentInfo, self).save(*args, **kwargs)
        self._original_comment = self.comment
