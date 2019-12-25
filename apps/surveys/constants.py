from django import forms
from django.utils.translation import ugettext_lazy as _

from surveys.widgets import SurveyTextInput, \
    SurveyTextarea, SurveyCheckboxInput, SurveyRadioSelect, \
    SurveyCheckboxSelectMultiple, SurveyNumberInput
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
    FieldType.NUMBER: forms.IntegerField,
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
    FieldType.NUMBER: SurveyNumberInput,
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


# Note: Field and choice labels could be patched in form builder
# for `FINAL` survey type. Make sure to keep their values in sync
# with `surveys.services` code.
TEMPLATES = {
    FormTemplates.COMMON: [
        {
            "id": 1,
            "label": "Материал курса для вас новый?",
            "order": 100,
            "required": True,
            "field_type": FieldType.RADIO_MULTIPLE,
            "visibility": FieldVisibility.VISIBLE,
            "input_name": "is_new_course",
            "choices": [
                {
                    "label": "Да, всё слышу впервые",
                    "value": 1
                },
                {
                    "label": "Что-то знаю, но, в основном, вся информация новая",
                    "value": 2
                },
                {
                    "label": "Большую часть знаю, но встречается что-то новое",
                    "value": 3
                },
                {
                    "label": "Весь материал мне известен",
                    "value": 4
                },
            ]
        },
        {
            "id": 2,
            "label": "Расскажите, где вы изучали эту тему раньше?",
            "show_label": False,
            "order": 200,
            "required": False,
            "field_type": FieldType.TEXTAREA,
            "placeholder": "Расскажите, где вы изучали эту тему раньше?",
            "visibility": FieldVisibility.HIDDEN,
            "input_name": "where_did_you_learn",
            "css_class": "_additional",
            "conditional_logic": [
                {
                    "action_type": "show",
                    "scope": "field",
                    "rules": [
                        {
                            "operator": "any",
                            "field_name": "is_new_course",
                            "value": [2, 3, 4]
                        }
                    ]
                },
            ]
        },
        {
            "id": 3,
            "label": "Что вы думаете о том, как проходят очные лекции?",
            "order": 300,
            "required": True,
            "field_type": FieldType.CHECKBOX_MULTIPLE,
            "visibility": FieldVisibility.VISIBLE,
            "input_name": "lectures_assessment",
            "choices": [
                {
                    "label": "Материал разбирается слишком быстро",
                    "value": 1
                },
                {
                    "label": "Материал разбирается слишком медленно",
                    "value": 2
                },
                {
                    "label": "Лектор не общается с аудиторией, и это вредит пониманию материала",
                    "value": 3
                },
                {
                    "label": "Преподаватель не отвечает на вопросы по материалу",
                    "value": 4
                },
                {
                    "label": "Тематика и чтение курса мне понравились, и я хочу продолжить изучение материала",
                    "value": 5
                },
            ]
        },
        {
            "id": 4,
            "label": "Возможно, некоторые темы остались непонятными. Отметьте занятия, на которых что-то осталось неясно, и напишите подробнее в поле для ответа",
            "order": 400,
            "required": False,
            "field_type": FieldType.CHECKBOX_MULTIPLE_WITH_NOTE,
            "visibility": FieldVisibility.VISIBLE,
            "free_answer": True,
            "conditional_logic": [
                {
                    "action_type": "create",
                    "scope": "choices",
                    "rules": [
                        {
                            "source": "CourseClass",
                            "field": "type",
                            "lookup_expr": "equal",
                            "value": 'lecture'
                        }
                    ]
                }
            ]
        },
        {
            "id": 5,
            "label": "Как вам кажется, прочитанный материал пригодится вам в будущем на работе? (Или, быть может, уже пригодился)",
            "order": 500,
            "required": True,
            "field_type": FieldType.RADIO_MULTIPLE,
            "visibility": FieldVisibility.VISIBLE,
            "choices": [
                {
                    "label": "Да, материал курса точно будет полезен",
                    "value": 1
                },
                {
                    "label": "Есть полезные моменты, но точно не всё",
                    "value": 2
                },
                {
                    "label": "Нет, думаю, мне ничего из этого не пригодится",
                    "value": 3
                },
            ]
        },
        {
            "id": 6,
            "label": "Вам понятно, как выставляется оценка по этому курсу?",
            "order": 600,
            "required": True,
            "field_type": FieldType.RADIO_MULTIPLE,
            "visibility": FieldVisibility.VISIBLE,
            "choices": [
                {
                    "label": "Да, схему объявили ещё в начале семестра, и она мне понятна",
                    "value": 1
                },
                {
                    "label": "Да, схему уже объявили (после начала курса), и она мне понятна",
                    "value": 2
                },
                {
                    "label": "Схему объявили, но я её не понимаю",
                    "value": 3
                },
                {
                    "label": "Я понимаю, как выставляется оценка, но мне это не кажется справедливым (поясню в конце анкеты)",
                    "value": 4
                },
                {
                    "label": "Нет, я не знаю, как выставляется оценка",
                    "value": 5
                },
            ]
        },
        {
            "id": 7,
            "label": "Дополнительные комментарии",
            "order": 70000,
            "required": False,
            "field_type": FieldType.TEXTAREA,
            "visibility": FieldVisibility.VISIBLE,
        },
        {
            "id": 8,
            "label": "Если хотите, представьтесь, пожалуйста",
            "order": 80000,
            "required": False,
            "field_type": FieldType.TEXT,
            "visibility": FieldVisibility.VISIBLE,
            "placeholder": "Фамилия Имя"
        },
    ],
    FormTemplates.VIDEO_SEMINAR: [
        {
            "id": 9,
            "label": "Как часто вы посещаете занятия?",
            "order": 700,
            "required": False,
            "field_type": FieldType.RADIO_MULTIPLE,
            "visibility": FieldVisibility.VISIBLE,
            "input_name": "attendance_frequency",
            "choices": [
                {
                    "label": "На занятия хожу по максимуму",
                    "value": 1
                },
                {
                    "label": "Чаще всего прихожу, но иногда пропускаю и смотрю видео",
                    "value": 2
                },
                {
                    "label": "Смотрю записи лекций и прихожу на семинары",
                    "value": 3
                },
                {
                    "label": "Обычно смотрю видео и не хожу на семинары",
                    "value": 4
                },
                {
                    "label": "Не смотрю видео и не хожу на занятия",
                    "value": 5
                },
            ]
        },
    ],
    FormTemplates.VIDEO_NO_SEMINAR: [
        {
            "id": 10,
            "label": "Как часто вы посещаете занятия?",
            "order": 700,
            "required": False,
            "field_type": FieldType.RADIO_MULTIPLE,
            "visibility": FieldVisibility.VISIBLE,
            "input_name": "attendance_frequency",
            "choices": [
                {
                    "label": "На занятия хожу по максимуму",
                    "value": 1
                },
                {
                    "label": "Чаще всего прихожу, но иногда пропускаю и смотрю видео",
                    "value": 2
                },
                {
                    "label": "Обычно смотрю видео и не хожу на занятия",
                    "value": 3
                },
                {
                    "label": "Не смотрю видео и не хожу на занятия",
                    "value": 4
                },
            ]
        },
    ],
    FormTemplates.SEMINAR: [
        {
            "id": 11,
            "label": "Практические занятия соответствуют прочитанным лекциям?",
            "order": 800,
            "required": False,
            "field_type": FieldType.RADIO_MULTIPLE,
            "visibility": FieldVisibility.VISIBLE,
            "input_name": "practice_lecture_compliance",
            "choices": [
                {
                    "label": "Да, практические занятия направлены на закрепление материала с лекций",
                    "value": 1
                },
                {
                    "label": "Нет, занятия оторваны от лекций и проходят независимо",
                    "value": 2
                },
                {
                    "label": "Нет, но это не подразумевается структурой курса",
                    "value": 3
                },
            ]
        },
        {
            "id": 12,
            "label": "Расскажите свои впечатления от семинаров",
            "show_label": False,
            "placeholder": "Расскажите свои впечатления от семинаров. Если занятия проходят в разных группах, то не забывайте указывать имена преподавателей",
            "order": 900,
            "required": False,
            "field_type": FieldType.TEXTAREA,
            "visibility": FieldVisibility.HIDDEN,
            "css_class": "_additional",
            "conditional_logic": [
                {
                    "action_type": "show",
                    "scope": "field",
                    "rules": [
                        {
                            "operator": "any",
                            "field_name": "practice_lecture_compliance",
                            "value": [2, 3]
                        }
                    ]
                },
            ]
        },
    ],
    FormTemplates.SEMINAR_HOMEWORK: [
        {
            "id": 13,
            "label": "Участие в семинарах помогает выполнять домашние задания?",
            "order": 1000,
            "required": False,
            "field_type": FieldType.RADIO_MULTIPLE,
            "visibility": FieldVisibility.VISIBLE,
            "input_name": "seminar_participation_benefit",
            "choices": [
                {
                    "label": "Да, практические занятия помогают справиться с домашними заданиями",
                    "value": 1
                },
                {
                    "label": "Нет, практические занятия не помогают при решении домашних заданий",
                    "value": 2
                },
            ]
        },
        {
            "id": 14,
            "label": "Какими материалами вы пользуетесь для выполнения заданий?",
            "show_label": False,
            "placeholder": "Какими материалами вы пользуетесь для выполнения заданий?",
            "order": 1100,
            "required": False,
            "field_type": FieldType.TEXTAREA,
            "visibility": FieldVisibility.HIDDEN,
            "css_class": "_additional",
            "conditional_logic": [
                {
                    "action_type": "show",
                    "scope": "field",
                    "rules": [
                        {
                            "operator": "any",
                            "field_name": "seminar_participation_benefit",
                            "value": [2]
                        }
                    ]
                },
            ]
        },
    ],
    FormTemplates.HOMEWORK: [
        {
            "id": 15,
            "label": "Оцените, пожалуйста, сколько часов в неделю вы тратите на выполнение домашних заданий",
            "order": 1200,
            "required": False,
            "field_type": FieldType.RADIO_MULTIPLE,
            "visibility": FieldVisibility.VISIBLE,
            "choices": [
                {
                    "label": "1-3 часа в неделю",
                    "value": 1
                },
                {
                    "label": "4-6 часов в неделю",
                    "value": 2
                },
                {
                    "label": "7-9 часов в неделю",
                    "value": 3
                },
                {
                    "label": "10 и более",
                    "value": 4
                },
            ]
        },
        {
            "id": 16,
            "label": "Задания соответствуют прочитанному материалу?",
            "order": 1300,
            "required": False,
            "field_type": FieldType.RADIO_MULTIPLE,
            "visibility": FieldVisibility.VISIBLE,
            "choices": [
                {
                    "label": "Да, для выполнения заданий мне хватает материала с занятий",
                    "value": 1
                },
                {
                    "label": "В целом, да, но мне приходится искать дополнительную информацию",
                    "value": 2
                },
                {
                    "label": "В целом, да, но не всегда всё понятно, и я спрашиваю у преподавателей",
                    "value": 3
                },
                {
                    "label": "Иногда связаны, а иногда нет (поясню в конце анкеты)",
                    "value": 4
                },
                {
                    "label": "Нет, домашние задания оторваны от занятий",
                    "value": 5
                },
            ]
        },
        {
            "id": 17,
            "label": "Вас устраивает скорость проверки домашних заданий?",
            "order": 1400,
            "required": False,
            "field_type": FieldType.RADIO_MULTIPLE,
            "visibility": FieldVisibility.VISIBLE,
            "input_name": "speed_check_hw",
            "choices": [
                {
                    "label": "Да, вполне",
                    "value": 1
                },
                {
                    "label": "Нет, не устраивает",
                    "value": 2
                },
            ]
        },
        {
            "id": 18,
            "label": "Поясните свой ответ",
            "show_label": False,
            "placeholder": "Поясните свой ответ",
            "order": 1500,
            "required": False,
            "field_type": FieldType.TEXTAREA,
            "visibility": FieldVisibility.HIDDEN,
            "css_class": "_additional",
            "conditional_logic": [
                {
                    "action_type": "show",
                    "scope": "field",
                    "rules": [
                        {
                            "operator": "any",
                            "field_name": "speed_check_hw",
                            "value": [2]
                        }
                    ]
                },
            ]
        },
    ],
    FormTemplates.ONLINE_COURSE: [
        {
            "id": 19,
            "label": "Что вы думаете про совмещение с онлайн-курсом?",
            "order": 1600,
            "required": False,
            "field_type": FieldType.TEXTAREA,
            "visibility": FieldVisibility.VISIBLE,
        },
    ]
}
