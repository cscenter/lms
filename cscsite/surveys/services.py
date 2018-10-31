from django.db.models import Q

from learning.models import CourseClass
from learning.utils import now_local
from surveys.constants import FormTemplates, STATUS_DRAFT, STATUS_TEMPLATE
from surveys.models import Form, FieldChoice, CourseSurvey

OFFLINE_COURSES_Q = ['lectures_assessment', 'attendance_frequency']


def course_form_builder(survey: CourseSurvey):
    co = survey.course_offering
    if survey.type in [CourseSurvey.MIDDLE]:
        pass
    form = Form(title=f'Опрос по курсу «{co}»',
                status=STATUS_DRAFT,
                slug=survey.type)
    form.save()

    templates = [FormTemplates.COMMON]
    seminar_type = CourseClass.TYPES.seminar
    has_seminars = co.courseclass_set.filter(type=seminar_type).exists()
    has_assignments = co.assignment_set.exists()
    if has_seminars:
        templates.append(FormTemplates.SEMINAR)
    if has_assignments:
        templates.append(FormTemplates.HOMEWORK)
    if has_seminars and has_assignments:
        templates.append(FormTemplates.SEMINAR_HOMEWORK)
    if co.has_classes_with_video:
        if has_seminars:
            templates.append(FormTemplates.VIDEO_SEMINAR)
        else:
            templates.append(FormTemplates.VIDEO_NO_SEMINAR)
    if co.online_course_url:
        templates.append(FormTemplates.ONLINE_COURSE)

    today_local = now_local(co.get_city())
    form_templates = Form.objects.filter(status=STATUS_TEMPLATE,
                                         slug__in=templates)
    for form_template in form_templates:
        fields = form_template.fields.all()
        for field in fields:
            # Crunch: For correspondence course hide questions about
            # offline lectures
            if co.is_correspondence and field.name in OFFLINE_COURSES_Q:
                continue
            source_field_choices = list(field.choices.all())
            # Mutate original field
            field.pk = None
            field.form_id = form.pk
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
                                    "course_offering": co,
                                    "date__lte": today_local.date()
                                }
                                if rule["value"] == "lecture":
                                    filters["type"] = CourseClass.TYPES.lecture
                                classes = (CourseClass.objects
                                           .filter(passed_lectures, **filters)
                                           .order_by("date", "starts_at"))
                                for i, c in enumerate(classes, start=next_index):
                                    choice = FieldChoice(value=i, label=c.name,
                                                         field=field)
                                    choice.save()
                                next_index += len(classes)
    return form
