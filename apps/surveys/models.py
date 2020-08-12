import json
from datetime import datetime
from typing import Optional, Tuple, List, Dict

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import formats
from django.utils.functional import cached_property
from django.utils.timezone import now, localtime
from django.utils.translation import gettext_lazy as _
from post_office import mail
from post_office.models import EmailTemplate

from core.timezone import now_local, TimezoneAwareModel, \
    TimezoneAwareDateTimeField
from core.urls import reverse, branch_aware_reverse
from courses.models import Course
from learning.models import Enrollment
from surveys.constants import FIELD_TYPES, MULTIPLE_CHOICE_FIELD_TYPES, \
    FieldType, FieldVisibility, STATUS_PUBLISHED, \
    STATUSES, FIELD_WIDGETS, STATUS_DRAFT, CHOICE_FIELD_TYPES


class FormManager(models.Manager):
    """
    Only show published forms for non-staff users.
    """
    def published(self, now_local: datetime, for_user=None):
        if for_user is not None and for_user.is_staff:
            return self.all()
        filters = [
            Q(status=STATUS_PUBLISHED),
        ]
        return self.filter(*filters)


class AbstractForm(models.Model):
    created = models.DateTimeField(
        verbose_name=_("created"),
        editable=False,
        default=now)
    title = models.CharField(
        verbose_name=_("Title"),
        max_length=255)
    slug = models.SlugField(_("Slug"))
    status = models.SmallIntegerField(
        verbose_name=_("Status"),
        choices=STATUSES,
        default=STATUS_DRAFT)
    description = models.TextField(
        verbose_name=_("Description"),
        blank=True)
    response = models.TextField(
        verbose_name=_("Response Message"),
        help_text=_("Shows this message after submitting form."),
        blank=True)

    objects = FormManager()

    class Meta:
        verbose_name = _("Form")
        verbose_name_plural = _("Forms")
        abstract = True

    def __str__(self):
        return self.title


class FieldManager(models.Manager):
    """
    Only show visible fields when displaying actual form..
    """
    def visible(self):
        return self.exclude(field_type=FieldType.HIDDEN)


class AbstractField(models.Model):
    PREFIX = 'field_'
    HIDDEN = FieldVisibility.HIDDEN
    VISIBLE = FieldVisibility.VISIBLE
    VISIBILITY_TYPES = (
        (HIDDEN, _("Hidden")),
        (VISIBLE, _("Visible")),
    )
    TYPES = FieldType
    created = models.DateTimeField(
        verbose_name=_("created"),
        editable=False,
        default=now)
    label = models.CharField(_("Label"), max_length=255)
    show_label = models.BooleanField(_("Show Label"), default=True)
    input_name = models.CharField(_("Input Name"), max_length=255, blank=True)
    order = models.IntegerField(_("Order"), null=True, blank=True)
    description = models.TextField(
        verbose_name=_("Description"),
        blank=True)
    required = models.BooleanField(_("Required"), default=True)
    field_type = models.SmallIntegerField(
        verbose_name=_("Field Type"),
        choices=FIELD_TYPES)
    # Use label as placeholder if NULL
    placeholder = models.CharField(
        verbose_name=_("Placeholder"),
        max_length=255,
        blank=True,
        null=True)
    field_css_classes = models.CharField(
        verbose_name=_("Field CSS classes"),
        max_length=128,
        blank=True)
    widget_css_classes = models.CharField(
        verbose_name=_("Widget CSS classes"),
        max_length=128,
        blank=True)
    visibility = models.SmallIntegerField(
        verbose_name=_("Visibility"),
        choices=VISIBILITY_TYPES,
        default=VISIBLE)
    help_text = models.TextField(
        verbose_name=_("Help Text"),
        blank=True,
        null=True)
    # TODO? Посмотреть как в гравити формс юзается
    error_message = models.CharField(
        verbose_name=_("Error Message"),
        max_length=255,
        blank=True,
        null=True)
    free_answer = models.BooleanField(
        _("Free Answer"),
        default=False)

    objects = FieldManager()

    class Meta:
        verbose_name = _("Field")
        verbose_name_plural = _("Fields")
        abstract = True

    @property
    def name(self):
        suffix = self.input_name if self.input_name else self.pk
        return self.get_field_name(suffix)

    @classmethod
    def get_field_name(cls, suffix):
        return f"{cls.PREFIX}{suffix}"

    def get_field_conditional_logic(self):
        logic = self.conditional_logic
        if not logic or not isinstance(logic, list):
            return None
        return json.dumps([x for x in logic if x.get('scope') == "field"])

    def __str__(self):
        return self.label


class AbstractFieldChoice(models.Model):
    """Choices for field types: radio buttons, checkboxes, selects"""
    created = models.DateTimeField(
        verbose_name=_("created"),
        editable=False,
        default=now)
    order = models.IntegerField(_("Order"), null=True, blank=True)
    label = models.CharField(_("Label"), max_length=255)
    value = models.CharField(_("Value"), max_length=255)
    # Makes sense for radio buttons
    default = models.BooleanField(_("Default"), default=False)
    free_answer = models.BooleanField(
        _("Free Answer"),
        help_text=_("Shows additional input for free answer if user "
                    "selected this variant."),
        default=False)

    class Meta:
        verbose_name = _("Field Choice")
        verbose_name_plural = _("Field Choices")
        abstract = True

    def __str__(self):
        return self.label


class AbstractFormSubmission(models.Model):
    created = models.DateTimeField(
        verbose_name=_("created"),
        editable=False,
        default=now)

    class Meta:
        verbose_name = _("Form Submission")
        verbose_name_plural = _("Form Submissions")
        abstract = True


class AbstractFieldEntry(models.Model):
    """A single field value for a submitted form."""
    field_id = models.IntegerField()
    value = models.TextField(null=True)
    is_choice = models.BooleanField(_("Is Choice"), default=False)
    meta = JSONField(_("Meta"), null=True, blank=True)

    class Meta:
        verbose_name = _("Form Submission Entry")
        verbose_name_plural = _("Form Submission Entries")
        abstract = True

    def __str__(self):
        return str(self.field_id)


class Form(AbstractForm):
    def clean(self):
        if self.status == STATUS_PUBLISHED:
            try:
                survey = self.survey
                today = now()
                if survey.expire_at <= today:
                    raise ValidationError({
                        "status": "Publishing expired course survey is not "
                                  "permitted"
                    })
            except CourseSurvey.DoesNotExist:
                pass

    @transaction.atomic
    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)


class CourseSurvey(TimezoneAwareModel, models.Model):
    TIMEZONE_AWARE_FIELD_NAME = 'course'

    MIDDLE = 'middle'
    FINAL = 'final'
    TYPES = (
        (MIDDLE, _("Middle")),
        (FINAL, _("Final")),
    )
    form = models.OneToOneField(Form,
                                related_name="survey",
                                primary_key=True,
                                on_delete=models.CASCADE)
    type = models.CharField(
        verbose_name=_("Type"),
        max_length=20,
        choices=TYPES)
    course = models.ForeignKey(Course,
                               related_name="surveys",
                               on_delete=models.CASCADE)
    expire_at = TimezoneAwareDateTimeField(
        verbose_name=_("Expires on"),
        help_text=_("With published selected, won't be shown after this time. "
                    "Datetime should be specified in the timezone of the root "
                    "course branch. Students will see deadline in MSK timezone"))
    email_template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.CASCADE,
        help_text=_("Students will receive notification based on this "
                    "template after form publication"),
        null=True, blank=True)
    students_notified = models.BooleanField(editable=False, default=False)

    class Meta:
        verbose_name = _("Course Survey")
        verbose_name_plural = _("Course Surveys")
        unique_together = [('course', 'type')]

    def __str__(self):
        branch = self.course.main_branch
        return f"{self.course}, {branch} [{self.type}]"

    def expire_at_local(self, tz=None, format=None):
        if not tz:
            tz = self.get_timezone()
        dt = localtime(self.expire_at, timezone=tz)
        return formats.date_format(dt, format) if format else dt

    @transaction.atomic
    def save(self, *args, **kwargs):
        from surveys.services import course_form_builder

        created = self.pk is None
        if created:
            if self.form_id is None:
                new_form = course_form_builder(self)
                self.form_id = new_form.pk
            if self.email_template is None:
                try:
                    template_name = self.get_email_template()
                    template = EmailTemplate.objects.get(name=template_name)
                    self.email_template_id = template.pk
                except EmailTemplate.DoesNotExist:
                    pass
        super().save(*args, **kwargs)

    def get_absolute_url(self, course: Course = None):
        course = course or self.course
        kwargs = {
            **course.url_kwargs,
            "survey_form_slug": self.form.slug
        }
        return branch_aware_reverse('surveys:form_detail', kwargs=kwargs)

    def get_report_url(self, output_format: str):
        return reverse("staff:exports_report_survey_submissions",
                       args=[self.pk, output_format])

    @property
    def title(self):
        return str(self.course)

    @property
    def is_published(self):
        return self.form.status == STATUS_PUBLISHED

    @property
    def is_active(self):
        today = now_local(self.course.get_timezone())
        expired = self.expire_at is not None and self.expire_at <= today
        return self.is_published and not expired

    def get_email_template(self):
        return f"survey-{self.type}"

    @classmethod
    def get_active(cls, course: Course) -> Optional["CourseSurvey"]:
        """Get the latest active survey for the course"""
        today = now_local(course.get_timezone())
        return (cls.objects
                .filter(Q(expire_at__gt=today) | Q(expire_at__isnull=True),
                        course=course,
                        form__status=STATUS_PUBLISHED)
                .order_by("-expire_at")
                .select_related("form")
                .first())


class Field(AbstractField):
    form = models.ForeignKey(Form,
                             related_name="fields",
                             on_delete=models.CASCADE)
    conditional_logic = JSONField(
        _("Conditional Logic"),
        help_text=_("Array of dictionaries with logic rules"),
        null=True, blank=True)

    def get_widget(self):
        return FIELD_WIDGETS.get(self.field_type)

    def has_choices(self):
        return self.field_type in CHOICE_FIELD_TYPES

    @cached_property
    def field_choices(self) -> Optional[List]:
        if self.has_choices():
            choices = []
            for field_choice in self.choices.all():
                choices.append((field_choice.value, field_choice.label))
            if self.field_type == FieldType.SELECT and not self.required:
                # The first OPTION with attr. value="" display only if...
                #   1. the db_field is not required
                #   2. the db_field is required and the default is not set
                text = self.placeholder if self.placeholder else ""
                choices.insert(0, ("", text))
            return choices

    @cached_property
    def field_choices_dict(self) -> Optional[Dict]:
        return {v: l for v, l in self.field_choices}

    @property
    def error_messages(self) -> Optional[dict]:
        # FIXME: кажется, что в таком виде не особо нужен error_message
        if self.error_message:
            return {
                'invalid': self.error_message
            }

    def get_placeholder(self):
        if self.has_choices():
            return None
        return self.placeholder

    def to_python_value(self, entries: List[AbstractFieldEntry]):
        """
        Converts entry values to the python format compatible with related
        form field.
        """
        if self.field_type in MULTIPLE_CHOICE_FIELD_TYPES:
            if self.field_type == FieldType.CHECKBOX_MULTIPLE_WITH_NOTE:
                selected_choices = []
                note = ""
                for e in entries:
                    if e.is_choice:
                        selected_choices.append(e.value)
                    else:
                        note = e.value
                value = [selected_choices, note]
            else:
                value = [e.value for e in entries]
            return value
        if len(entries) == 1:
            return entries[0].value
        return None

    def to_db_value(self, python_value) -> List[Tuple[str, bool]]:
        """
        Converts form field value to the format convenient for storage
        in the DB.
        """
        if not python_value:
            return []
        if self.field_type == FieldType.CHECKBOX_MULTIPLE_WITH_NOTE:
            checkboxes, note = python_value
            values = [(v, True) for v in checkboxes]
            if note:
                values.append((note, False))
        elif isinstance(python_value, list):
            values = [(v.strip(), True) for v in python_value]
        else:
            values = [(python_value, self.has_choices())]
        return values

    def to_export_value(self, entries: List[AbstractFieldEntry]) -> List[str]:
        """
        Converts field entries to human readable format, for fields with
        multiple answers order depends on `.field_choices` elements order.
        """
        if not entries:
            return []
        if self.has_choices():
            choices = set()
            note = None  # Expected only 1 note per field
            for e in entries:
                if e.is_choice:
                    choices.add(e.value)
                else:
                    note = e.value
            # Entries could be unsorted, but choices should
            value = [self.field_choices_dict[v] for v in self.field_choices_dict
                     if v in choices]
            if note:
                value.append(note)
            return value
        else:
            return [entries[0].value]

    def clean(self):
        if self.conditional_logic is not None:
            if not isinstance(self.conditional_logic, list):
                raise ValidationError({
                    "conditional_logic": "Conditional Logic use only array "
                                         "as a wrapper"
                })
            if any(True for logic_block in self.conditional_logic
                   if not isinstance(logic_block, dict)):
                raise ValidationError({
                    "conditional_logic": "Supported type for Conditional "
                                         "Logic is List[dict]"
                })

    def save(self, *args, **kwargs):
        if self.order is None:
            # Make an ordering gap between neighbour fields
            self.order = self.form.fields.count() * 10 + 10
        super().save(*args, **kwargs)


class FieldChoice(AbstractFieldChoice):
    field = models.ForeignKey(
        Field,
        related_name="choices",
        on_delete=models.CASCADE,
        limit_choices_to={
            "field_type__in": CHOICE_FIELD_TYPES
        })

    def save(self, *args, **kwargs):
        if self.order is None:
            # Make an ordering gap between neighbour fields
            self.order = self.field.choices.count() * 10 + 10
        super().save(*args, **kwargs)


class FormSubmission(AbstractFormSubmission):
    form = models.ForeignKey(Form, related_name="submissions",
                             on_delete=models.CASCADE)

    def __str__(self):
        return self.form.title


class FieldEntry(AbstractFieldEntry):
    # Denormalization
    form = models.ForeignKey(Form, related_name="entries", editable=False,
                             on_delete=models.CASCADE)
    submission = models.ForeignKey(FormSubmission,
                                   related_name="entries",
                                   on_delete=models.CASCADE)
