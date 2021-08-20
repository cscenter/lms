from typing import Any, List

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Submit

from django import forms

from core.forms import CANCEL_BUTTON
from courses.models import Course, CourseTeacher, StudentGroupTypes
from learning.models import StudentGroup


class AssigneeModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: CourseTeacher):
        return obj.teacher.get_full_name(last_name_first=True)


class StudentGroupCreateForm(forms.ModelForm):
    assignee = AssigneeModelChoiceField(
        label='Ответственный',
        queryset=CourseTeacher.objects.none(),
        required=False)

    class Meta:
        model = StudentGroup
        # FIXME: проверять уникальность имени
        fields = ('name', 'assignee')

    def __init__(self, course: Course, **kwargs: Any):
        super().__init__(**kwargs)
        self.instance.course = course
        self.instance.type = StudentGroupTypes.MANUAL
        course_teachers = (CourseTeacher.objects
                           .filter(course=course)
                           .select_related('teacher'))
        self.fields['assignee'].queryset = course_teachers
        self.helper = FormHelper(self)
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Добавить'))
        self.helper.add_input(CANCEL_BUTTON)
