from textwrap import dedent

from django.db import migrations, connection

from surveys.constants import STATUS_TEMPLATE, TEMPLATES


def create_course_survey_templates(apps, schema_editor):
    Form = apps.get_model('surveys', 'Form')
    Field = apps.get_model('surveys', 'Field')
    FieldChoice = apps.get_model('surveys', 'FieldChoice')

    for form_template, fields in TEMPLATES.items():
        form, _ = Form.objects.get_or_create(
            status=STATUS_TEMPLATE,
            slug=form_template,
            defaults={"title": form_template})
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
