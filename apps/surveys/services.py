import copy
from textwrap import dedent

from post_office import mail
from post_office.models import EmailTemplate

from django.db.models import Q

from core.timezone import now_local
from courses.constants import ClassTypes
from courses.models import CourseClass
from learning.models import Enrollment
from surveys.constants import STATUS_DRAFT, STATUS_TEMPLATE, TEMPLATES, FormTemplates
from surveys.models import CourseSurvey, Field, FieldChoice, Form

OFFLINE_COURSES_Q = ['lectures_assessment', 'attendance_frequency']


def create_survey_notifications(survey: CourseSurvey):
    if not survey.email_template_id or survey.students_notified:
        return
    course = survey.course
    context = {
        "COURSE_NAME": str(course),
        "SURVEY_URL": survey.get_absolute_url()
    }
    active_enrollments = (Enrollment.active.can_submit_assignments()
                          .filter(course=course.pk)
                          .select_related("student"))
    for e in active_enrollments.iterator():
        mail.send(
            [e.student.email],
            sender="noreply@compscicenter.ru",
            template=survey.email_template,
            context=context,
            render_on_delivery=True,
            backend='ses',
        )
    survey.students_notified = True
    survey.save(update_fields=["students_notified"])


def _update_field_label(survey, field):
    """For FINAL survey show labels in the past form"""
    if survey.type != survey.FINAL:
        return
    labels = {
        "Что вы думаете о том, как проходят очные лекции?": "Что вы думаете о том, как проходили очные лекции?",
        "Как часто вы посещаете занятия?": "Как часто вы посещали занятия?",
        "Какими материалами вы пользуетесь для выполнения заданий?": "Какими материалами вы пользовались для выполнения заданий?",
        "Оцените, пожалуйста, сколько часов в неделю вы тратите на выполнение домашних заданий": "Оцените, пожалуйста, сколько часов в неделю вы тратили на выполнение домашних заданий",
        "Задания соответствуют прочитанному материалу?": "Задания соответствовали прочитанному материалу?",
        "Вас устраивает скорость проверки домашних заданий?": "Вас устраивала скорость проверки домашних заданий?",
        "Практические занятия соответствуют прочитанным лекциям?": "Практические занятия соответствовали прочитанным лекциям?",
    }
    if field.label in labels:
        field.label = labels[field.label]


def _update_field_choice_label(survey, field_choice):
    """For FINAL survey show choice labels in the past form"""
    if survey.type != survey.FINAL:
        return
    labels = {
        "Материал разбирается слишком медленно": "Материал разбирался слишком медленно",
        "Материал разбирается слишком быстро": "Материал разбирался слишком быстро",
        "Лектор не общается с аудиторией, и это вредит пониманию материала": "Лектор не общался с аудиторией, и это вредило пониманию материала",
        "Преподаватель не отвечает на вопросы по материалу": "Преподаватель не отвечал на вопросы по материалу",
        "Да, для выполнения заданий мне хватает материала с занятий": "Да, для выполнения заданий мне хватало материала с занятий",
        "В целом, да, но мне приходится искать дополнительную информацию": "В целом, да, но мне приходилось искать дополнительную информацию",
        "В целом, да, но не всегда всё понятно, и я спрашиваю у преподавателей": "В целом, да, но не всегда всё понятно, и я спрашивал у преподавателей",
        "Нет, домашние задания оторваны от занятий": "Нет, домашние задания были оторваны от занятий",
        "Нет, не устраивает": "Нет, не устраивала",
        "Да, практические занятия направлены на закрепление материала с лекций": "Да, практические занятия были направлены на закрепление материала с лекций",
        "Нет, занятия оторваны от лекций и проходят независимо": "Нет, занятия были оторваны от лекций и проходили независимо",
        "Нет, но это не подразумевается структурой курса": "Нет, но это не подразумевалось структурой курса",
    }
    if field_choice.label in labels:
        field_choice.label = labels[field_choice.label]


def course_form_builder(survey: CourseSurvey):
    course = survey.course
    if survey.type in [CourseSurvey.MIDDLE]:
        pass
    form = Form(title=f'Опрос по курсу «{course}»',
                status=STATUS_DRAFT,
                slug=survey.type)
    form.save()

    templates = [FormTemplates.COMMON]
    seminar_type = ClassTypes.SEMINAR
    has_seminars = course.courseclass_set.filter(type=seminar_type).exists()
    has_assignments = course.assignment_set.exists()
    if has_seminars:
        templates.append(FormTemplates.SEMINAR)
    if has_assignments:
        templates.append(FormTemplates.HOMEWORK)
    if has_seminars and has_assignments:
        templates.append(FormTemplates.SEMINAR_HOMEWORK)
    if course.public_videos_count:
        if has_seminars:
            templates.append(FormTemplates.VIDEO_SEMINAR)
        else:
            templates.append(FormTemplates.VIDEO_NO_SEMINAR)
    if course.online_course_url:
        templates.append(FormTemplates.ONLINE_COURSE)

    today_local = now_local(course.get_timezone())
    form_templates = Form.objects.filter(status=STATUS_TEMPLATE,
                                         slug__in=templates)
    has_additional_branches = course.branches.count() > 1
    for form_template in form_templates:
        fields = form_template.fields.all()
        for field in fields:
            # Crunch: For correspondence course hide questions about
            # offline lectures
            if has_additional_branches and field.name in OFFLINE_COURSES_Q:
                continue
            source_field_choices = list(field.choices.all())
            # Mutate original field
            field.pk = None
            field.form_id = form.pk
            _update_field_label(survey, field)
            field.save()

            next_index = 1
            for choice in source_field_choices:
                choice.pk = None
                choice.field_id = field.pk
                _update_field_choice_label(survey, choice)
                choice.save()
                next_index += 1
            # Populate choices based on conditional logic
            if field.conditional_logic:
                passed_lectures = (Q(date__lt=today_local.date()) |
                                   Q(date__exact=today_local.date(),
                                     ends_at__lt=today_local.time()))
                for l in field.conditional_logic:
                    if (l.get('scope') == 'choices'
                            and l.get('action_type') == 'create'):
                        for rule in l.get("rules", []):
                            if rule.get('source') == "CourseClass":
                                filters = {
                                    "course": course,
                                    "date__lte": today_local.date()
                                }
                                if rule["value"] == "lecture":
                                    filters["type"] = ClassTypes.LECTURE
                                classes = (CourseClass.objects
                                           .filter(passed_lectures, **filters)
                                           .order_by("date", "starts_at"))
                                for i, c in enumerate(classes, start=next_index):
                                    choice = FieldChoice(value=i, label=c.name,
                                                         field=field)
                                    choice.save()
                                next_index += len(classes)
    return form


def create_course_survey_templates():
    form_templates = copy.deepcopy(TEMPLATES)
    for form_template, fields in form_templates.items():
        form, created = Form.objects.get_or_create(
            status=STATUS_TEMPLATE,
            slug=form_template,
            defaults={"title": form_template})
        if created:
            for field in fields:
                choices = []
                if "choices" in field:
                    choices = field["choices"]
                    del field["choices"]
                field, _ = Field.objects.get_or_create(form_id=form.id,
                                                       label=field["label"],
                                                       defaults=field)
                for index, choice in enumerate(choices, start=1):
                    if "order" not in choice:
                        choice["order"] = index * 10
                    FieldChoice.objects.get_or_create(field_id=field.id,
                                                      label=choice["label"],
                                                      defaults=choice)


def create_survey_email_templates():
    email_templates = [
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
    for template in email_templates:
        EmailTemplate.objects.get_or_create(name=template["name"],
                                            defaults=template)
