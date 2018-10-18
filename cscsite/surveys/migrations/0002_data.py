from textwrap import dedent

from django.db import migrations, connection

from surveys.constants import FormTemplates, FieldType, FieldVisibility, \
    STATUS_DRAFT, STATUS_TEMPLATE

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
            "placeholder": "Расскажите свои впечатления от семинаров",
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
                            "value": [3]
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


def create_course_survey_templates(apps, schema_editor):
    Form = apps.get_model('surveys', 'Form')
    Field = apps.get_model('surveys', 'Field')
    FieldChoice = apps.get_model('surveys', 'FieldChoice')

    for form_template, fields in TEMPLATES.items():
        form, _ = Form.objects.get_or_create(
            status=STATUS_TEMPLATE,
            slug=form_template,
            defaults={"status": STATUS_DRAFT, "title": form_template})
        for field in fields:
            choices = []
            if "choices" in field:
                choices = field["choices"]
                del field["choices"]
            field, _ = Field.objects.get_or_create(form_id=form.id,
                                                   id=field["id"],
                                                   defaults=field)
            for index, choice in enumerate(choices, start=1):
                if "order" not in choice:
                    choice["order"] = index * 10
                FieldChoice.objects.get_or_create(field_id=field.id,
                                                  label=choice["label"],
                                                  defaults=choice)

    with connection.cursor() as cursor:
        cursor.execute(f"""
        SELECT setval(pg_get_serial_sequence('"{Field._meta.db_table}"','id'), coalesce(max(id), 1), max(id) IS NOT null) 
        FROM "{Field._meta.db_table}";
        """)


def create_survey_email_templates(apps, schema_editor):
    templates = [
        {
            "name": "survey-middle",
            "subject": "Курс «{{ COURSE_NAME }}» - промежуточный опрос",
            "description": "Уведомление студентам курса о публикации опроса",
            "content": dedent("""\
                Добрый день! 

                На сайте появился промежуточный опрос по курсу «{{ COURSE_NAME }}»: {{ SURVEY_URL }}. Пожалуйста, ответьте на вопросы максимально подробно в течение недели. Ваши ответы помогут кураторам выяснить проблемы и решить их уже в этом семестре. 

                Доступ к ответам есть только у кураторов. Если вы не подпишетесь, мы не узнаем, кто именно заполнил анкету. 

                Спасибо!

                Кураторы центра
                
                Это письмо отправлено автоматически и не требует ответа.""")
        },
        {
            "name": "survey-final",
            "subject": "Курс «{{ COURSE_NAME }}» - финальный опрос",
            "description": "Уведомление студентам курса о публикации опроса",
            "content": dedent("""\
                Добрый день! 

                На сайте появился финальный опрос по курсу «{{ COURSE_NAME }}»: {{ SURVEY_URL }}. Пожалуйста, ответьте на вопросы максимально подробно в течение недели. Ваши ответы помогут кураторам выяснить проблемы и решить их уже в этом семестре. 

                Доступ к ответам есть только у кураторов. Если вы не подпишетесь, мы не узнаем, кто именно заполнил анкету. 

                Спасибо!

                Кураторы центра
                
                Это письмо отправлено автоматически и не требует ответа.""")
        }
    ]
    for template in templates:
        EmailTemplate = apps.get_model('post_office', 'EmailTemplate')
        EmailTemplate.objects.get_or_create(name=template["name"],
                                            defaults=template)


class Migration(migrations.Migration):
    dependencies = [
        ('surveys', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_course_survey_templates),
        migrations.RunPython(create_survey_email_templates),
    ]
