from learning.models import CourseOffering, CourseClass
from surveys.constants import FormTemplates
from surveys.models import Form, FieldChoice

OFFLINE_COURSES_Q = ['lectures_assessment', 'attendance_frequency']


def course_form_builder(course_offering: CourseOffering, survey_type):
    co = course_offering
    form = Form(title=f'Опрос по курсу «{co}»', slug=survey_type)
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

    form_templates = Form.objects.filter(is_template=True, slug__in=templates)
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
            field.is_template = False
            field.save()

            next_index = 1
            for choice in source_field_choices:
                choice.pk = None
                choice.field_id = field.pk
                choice.save()
                next_index += 1
            # Populate choices based on conditional logic
            if field.conditional_logic:
                for l in field.conditional_logic:
                    if (l.get('scope') == 'choices'
                            and l.get('action_type') == 'create'):
                        for rule in l.get("rules", []):
                            if rule.get('source') == "CourseClass":
                                filters = {"course_offering": co}
                                if rule["value"] == "lecture":
                                    filters["type"] = CourseClass.TYPES.lecture
                                classes = (CourseClass.objects
                                           .filter(**filters)
                                           .order_by("date", "starts_at"))
                                for i, c in enumerate(classes, start=next_index):
                                    choice = FieldChoice(value=i, label=c.name,
                                                         field=field)
                                    choice.save()
                                next_index += len(classes)
    return form
