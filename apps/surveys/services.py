from django.db.models import Q

from courses.models import CourseClass
from courses.settings import ClassTypes
from core.timezone import now_local
from surveys.constants import FormTemplates, STATUS_DRAFT, STATUS_TEMPLATE
from surveys.models import Form, FieldChoice, CourseSurvey

OFFLINE_COURSES_Q = ['lectures_assessment', 'attendance_frequency']


def _update_field_label(field):
    """For FINAL survey type show labels in the past form"""
    labels = {
        "Что вы думаете о том, как проходят очные лекции?": "Что вы думаете о том, как проходили очные лекции?",
        "Как часто вы посещаете занятия?": "Как часто вы посещали занятия?",
        "Какими материалами вы пользуетесь для выполнения заданий?": "Какими материалами вы пользовались для выполнения заданий?",
        "Оцените, пожалуйста, сколько часов в неделю вы тратите на выполнение домашних заданий": "Оцените, пожалуйста, сколько часов в неделю вы тратили на выполнение домашних заданий"
    }
    if field.label in labels:
        field.label = labels[field.label]


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
    if course.has_classes_with_video:
        if has_seminars:
            templates.append(FormTemplates.VIDEO_SEMINAR)
        else:
            templates.append(FormTemplates.VIDEO_NO_SEMINAR)
    if course.online_course_url:
        templates.append(FormTemplates.ONLINE_COURSE)

    today_local = now_local(course.get_city())
    form_templates = Form.objects.filter(status=STATUS_TEMPLATE,
                                         slug__in=templates)
    for form_template in form_templates:
        fields = form_template.fields.all()
        for field in fields:
            # Crunch: For correspondence course hide questions about
            # offline lectures
            if course.is_correspondence and field.name in OFFLINE_COURSES_Q:
                continue
            source_field_choices = list(field.choices.all())
            # Mutate original field
            field.pk = None
            field.form_id = form.pk
            if survey.type == survey.FINAL:
                _update_field_label(field)
            field.save()

            next_index = 1
            for choice in source_field_choices:
                choice.pk = None
                choice.field_id = field.pk
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
