from django import forms
from django.utils.translation import ugettext_lazy as _

from surveys.widgets import SurveyTextInput, \
    SurveyTextarea, SurveyCheckboxInput, SurveyRadioSelect, \
    SurveyCheckboxSelectMultiple
from surveys.fields import SurveyChoiceField, SurveyMultipleChoiceField, \
    SurveyMultipleChoiceFreeAnswerField

STATUS_DRAFT = 0
STATUS_PUBLISHED = 1
STATUS_TEMPLATE = 2
STATUSES = (
    (STATUS_DRAFT, _("Draft")),
    (STATUS_PUBLISHED, _("Published")),
    (STATUS_TEMPLATE, _("Template")),
)


# TODO: make as enum
class FieldType:
    TEXT = 1
    TEXTAREA = 2
    EMAIL = 3
    CHECKBOX = 4
    CHECKBOX_MULTIPLE = 5
    SELECT = 6
    SELECT_MULTIPLE = 7
    RADIO_MULTIPLE = 8
    FILE = 9
    DATE = 10
    DATE_TIME = 11
    HIDDEN = 12
    NUMBER = 13
    URL = 14
    CHECKBOX_MULTIPLE_WITH_NOTE = 15


class FieldVisibility:
    HIDDEN = 0
    VISIBLE = 1


FIELD_TYPES = (
    (FieldType.TEXT, _("Single line text")),
    (FieldType.TEXTAREA, _("Multi line text")),
    (FieldType.EMAIL, _("Email")),
    (FieldType.NUMBER, _("Number")),
    (FieldType.URL, _("URL")),
    (FieldType.CHECKBOX, _("Check box")),
    (FieldType.CHECKBOX_MULTIPLE, _("Check boxes")),
    (FieldType.CHECKBOX_MULTIPLE_WITH_NOTE, _("Check boxes with textarea")),
    (FieldType.SELECT, _("Drop down")),
    (FieldType.SELECT_MULTIPLE, _("Multi select")),
    (FieldType.RADIO_MULTIPLE, _("Radio buttons")),
    (FieldType.DATE, _("Date")),
    (FieldType.DATE_TIME, _("Date/time")),
)

# Field classes for all available field types.
FIELD_CLASSES = {
    FieldType.TEXT: forms.CharField,
    FieldType.TEXTAREA: forms.CharField,
    FieldType.CHECKBOX: forms.BooleanField,
    FieldType.CHECKBOX_MULTIPLE: SurveyMultipleChoiceField,
    FieldType.CHECKBOX_MULTIPLE_WITH_NOTE: SurveyMultipleChoiceFreeAnswerField,
    FieldType.SELECT: forms.ChoiceField,
    FieldType.SELECT_MULTIPLE: SurveyMultipleChoiceField,
    FieldType.RADIO_MULTIPLE: SurveyChoiceField,
    FieldType.FILE: forms.FileField,
    FieldType.DATE: forms.DateField,
    FieldType.DATE_TIME: forms.DateTimeField,
}

# Widgets for field types where a specialised widget is required.
FIELD_WIDGETS = {
    FieldType.TEXT: SurveyTextInput,
    FieldType.TEXTAREA: SurveyTextarea,
    FieldType.CHECKBOX: SurveyCheckboxInput,
    FieldType.CHECKBOX_MULTIPLE: SurveyCheckboxSelectMultiple,
    FieldType.RADIO_MULTIPLE: SurveyRadioSelect,
}

CHOICE_FIELD_TYPES = [
    FieldType.CHECKBOX_MULTIPLE,
    FieldType.CHECKBOX_MULTIPLE_WITH_NOTE,
    FieldType.SELECT,
    FieldType.SELECT_MULTIPLE,
    FieldType.RADIO_MULTIPLE
]

MULTIPLE_CHOICE_FIELD_TYPES = [
    FieldType.CHECKBOX_MULTIPLE,
    FieldType.CHECKBOX_MULTIPLE_WITH_NOTE,
    FieldType.SELECT_MULTIPLE,
]

FREE_ANSWER_SUPPORT = [
    FieldType.CHECKBOX_MULTIPLE,
    FieldType.RADIO_MULTIPLE
]

FIELD_MAX_LENGTH = 255

TEMPLATE_PACK = 'surveys'
DEFAULT_WIDGET = SurveyTextInput


class FormTemplates:
    COMMON = "COMMON"
    VIDEO_SEMINAR = "VIDEO_SEMINAR"
    VIDEO_NO_SEMINAR = "VIDEO_NO_SEMINAR"
    SEMINAR = "SEMINAR"
    SEMINAR_HOMEWORK = "SEMINAR_HOMEWORK"
    HOMEWORK = "HOMEWORK"
    ONLINE_COURSE = "ONLINE_COURSE"


COURSE_FORM_TEMPLATES = [
    FormTemplates.COMMON,
    FormTemplates.VIDEO_SEMINAR,
    FormTemplates.VIDEO_NO_SEMINAR,
    FormTemplates.SEMINAR,
    FormTemplates.SEMINAR_HOMEWORK,
    FormTemplates.HOMEWORK,
    FormTemplates.ONLINE_COURSE,
]

