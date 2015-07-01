from __future__ import unicode_literals, absolute_import

import logging

from model_utils import Choices
from model_utils.fields import MonitorField
from model_utils.models import TimeStampedModel
from sorl.thumbnail import ImageField

from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
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


class CSCUserQuerySet(models.query.QuerySet):
    _lexeme_trans_map = dict((ord(c), None) for c in '*|&:')

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

    def search_names(self, qstr):
        qstr = qstr.strip()
        tsquery = self._form_name_tsquery(qstr)
        if tsquery is None:
            return self.none()
        else:
            return (self
                    .extra(where=["to_tsvector(first_name || ' ' || last_name) "
                                  "@@ to_tsquery(%s)"],
                           params=[tsquery])
                    .exclude(first_name__exact='',
                             last_name__exact=''))


class CustomUserManager(UserManager.from_queryset(CSCUserQuerySet)):
    use_in_migrations = False


@python_2_unicode_compatible
class CSCUser(AbstractUser):

    # FIXME: replace `groups__name` with groups__pk in learning.signals
    group_pks = Choices(
        (1, 'STUDENT_CENTER', _('Student [CENTER]')),
        (2, 'TEACHER_CENTER', _('Teacher [CENTER]')),
        (3, 'GRADUATE_CENTER', _('Graduate')),
        (4, 'VOLUNTEER', _('Volunteer')),
        (5, 'STUDENT_CLUB', _('Student [CLUB]')),
        (6, 'TEACHER_CLUB', _('Teacher [CLUB]')),
    )

    STATUS = Choices(('expelled', _("StudentInfo|Expelled")),
                     ('reinstated', _("StudentInfo|Reinstalled")),
                     ('will_graduate', _("StudentInfo|Will graduate")))

    GENDER_MALE = 'M'
    GENDER_FEMALE = 'F'
    GENDER_CHOICES = (
        (GENDER_MALE, _('Male')),
        (GENDER_FEMALE, _('Female')),
    )
    gender = models.CharField(_("Gender"), max_length=1, choices=GENDER_CHOICES)

    _original_comment = None

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
    is_center_student = models.BooleanField(
        _("Student of CSCenter"),
        help_text=_("Students without this flag belong to CSClub only "
                    "and can't enroll to CSCenter's courses"),
        default=False)
    # internal student info
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
    nondegree = models.BooleanField(
        _("Non-degree student"),
        default=False)
    status = models.CharField(
        choices=STATUS,
        verbose_name=_("Status"),
        max_length=15,
        blank=True)
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
        return self.group_pks.STUDENT_CENTER in self._cs_group_pks or \
               self.group_pks.STUDENT_CLUB in self._cs_group_pks

    @property
    def is_teacher(self):
        return self.group_pks.TEACHER_CENTER in self._cs_group_pks or \
               self.group_pks.TEACHER_CLUB in self._cs_group_pks

    @property
    def is_graduate(self):
        return self.group_pks.GRADUATE_CENTER in self._cs_group_pks


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
    student = models.ForeignKey(
        CSCUser,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)
    name = models.CharField(_("Course|name"), max_length=255)
    grade = models.PositiveSmallIntegerField(
        _("Grade"),
        validators=[MinValueValidator(2), MaxValueValidator(5)],
        help_text=_("from 2 to 5, inclusive"),
        null=True,
        blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("SHAD course record")
        verbose_name_plural = _("SHAD course records")

    def __str__(self):
        return smart_text(self.name)


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
