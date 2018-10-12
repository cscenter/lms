import json
from datetime import datetime
from typing import Optional, Tuple, Any, List

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.db.transaction import atomic
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from core.utils import city_aware_reverse
from learning.models import CourseOffering
from surveys.constants import FIELD_TYPES, FIELD_MAX_LENGTH, \
    MULTIPLE_CHOICE_FIELD_TYPES, FieldType, FieldVisibility, STATUS_PUBLISHED, \
    STATUSES, FIELD_WIDGETS


class FormManager(models.Manager):
    """
    Only show published forms for non-staff users.
    """
    def published(self, now_local: datetime, for_user=None):
        if for_user is not None and for_user.is_staff:
            return self.all()
        filters = [
            Q(publish_at__lte=now_local) | Q(publish_at__isnull=True),
            Q(expire_at__gte=now_local) | Q(expire_at__isnull=True),
            Q(status=STATUS_PUBLISHED),
            Q(is_template=False),
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
        default=STATUS_PUBLISHED)
    publish_at = models.DateTimeField(
        verbose_name=_("Published from"),
        help_text=_("With published selected, won't be shown until this time."),
        blank=True, null=True)
    expire_at = models.DateTimeField(
        verbose_name=_("Expires on"),
        help_text=_("With published selected, won't be shown after this time."),
        blank=True, null=True)
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
    created = models.DateTimeField(
        verbose_name=_("created"),
        editable=False,
        default=now)
    label = models.CharField(_("Label"), max_length=255)
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
    css_class = models.CharField(
        verbose_name=_("Widget classes"),
        max_length=255,
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
    value = models.CharField(max_length=FIELD_MAX_LENGTH, null=True)
    is_choice = models.BooleanField(_("Is Choice"), default=False)
    meta = JSONField(_("Meta"), null=True, blank=True)

    class Meta:
        verbose_name = _("Form Submission Entry")
        verbose_name_plural = _("Form Submission Entries")
        abstract = True

    def __str__(self):
        return str(self.field_id)


class Form(AbstractForm):
    is_template = models.BooleanField(_("Template"), default=False)


class CourseOfferingSurvey(models.Model):
    MIDDLE = 'middle'
    FINAL = 'final'
    TYPES = (
        (MIDDLE, _("Middle")),
        (FINAL, _("Final")),
    )
    form = models.OneToOneField(Form,
                                related_name="course_form",
                                primary_key=True,
                                on_delete=models.CASCADE)
    type = models.CharField(
        verbose_name=_("Type"),
        max_length=20,
        choices=TYPES)
    course_offering = models.ForeignKey(CourseOffering,
                                        related_name="surveys",
                                        on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Course Survey")
        verbose_name_plural = _("Course Surveys")
        unique_together = [('course_offering', 'type')]

    @transaction.atomic
    def save(self, *args, **kwargs):
        from surveys.services import course_form_builder

        created = self.pk is None
        if created and self.form_id is None:
            new_form = course_form_builder(self.course_offering, self.type)
            self.form_id = new_form.pk
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        kwargs = {
            "course_slug": self.course_offering.course.slug,
            "semester_type": self.course_offering.semester.type,
            "semester_year": self.course_offering.semester.year,
            "city_code": self.course_offering.get_city(),
            "slug": self.form.slug
        }
        return city_aware_reverse('surveys:form_detail', kwargs=kwargs)


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

    @cached_property
    def field_choices(self) -> Optional[List]:
        if self.field_type in MULTIPLE_CHOICE_FIELD_TYPES:
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

    @property
    def error_messages(self) -> Optional[dict]:
        # FIXME: кажется, что в таком виде не особо нужен error_message
        if self.error_message:
            return {
                'invalid': self.error_message
            }

    def get_placeholder(self):
        if self.field_type in MULTIPLE_CHOICE_FIELD_TYPES:
            return None
        return self.placeholder

    def to_field_value(self, entries: List[AbstractFieldEntry]):
        """
        Converts entry values to the python format compatible with related
        form field.
        """
        if self.field_type in MULTIPLE_CHOICE_FIELD_TYPES:
            if self.field_type == FieldType.CHECKBOX_MULTIPLE_WITH_NOTE:
                choices = []
                note = ""
                for e in entries:
                    if e.is_choice:
                        choices.append(e.value)
                    else:
                        note = e.value
                value = [choices, note]
            else:
                value = [e.value for e in entries]
            return value
        if len(entries) == 1:
            return entries[0].value
        return None

    def prepare_field_value(self, value) -> List[Tuple[str, bool]]:
        if not value:
            return []
        if self.field_type == FieldType.CHECKBOX_MULTIPLE_WITH_NOTE:
            checkboxes, note = value
            values = [(v, True) for v in checkboxes]
            values.append((note, False))
        elif isinstance(value, list):
            values = [(v.strip(), True) for v in value]
        else:
            values = [(value, False)]
        return values

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
            "field_type__in": MULTIPLE_CHOICE_FIELD_TYPES
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
