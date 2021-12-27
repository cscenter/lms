from typing import Any

from crispy_forms.helper import FormHelper

from django import forms
from django.db.models import Q

from courses.models import Course, CourseTeacher, StudentGroupTypes
from courses.selectors import get_teachers
from learning.models import StudentGroup
from learning.services import StudentGroupService


class AssigneeModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: CourseTeacher):
        return obj.teacher.get_full_name(last_name_first=True)


class StudentGroupForm(forms.ModelForm):
    assignee = AssigneeModelChoiceField(
        label='Ответственный',
        queryset=CourseTeacher.objects.none(),
        required=False)

    class Meta:
        model = StudentGroup
        fields = ('name', 'assignee')

    def __init__(self, course: Course, **kwargs: Any):
        super().__init__(**kwargs)
        self.instance.course = course
        # Set type for new student groups
        if self.instance.pk is None:
            self.instance.type = StudentGroupTypes.MANUAL
        filters = [
            Q(course=course),
            Q(roles=~CourseTeacher.roles.spectator)
        ]
        course_teachers = get_teachers(filters=filters)
        self.fields['assignee'].queryset = course_teachers
        self.helper = FormHelper(self)
        self.helper.form_tag = False


class StudentGroupStudentsTransferForm(forms.Form):
    student_group = forms.ChoiceField(
        label="Новая группа",
        choices=(),
        required=True)

    def __init__(self, student_group: StudentGroup, **kwargs: Any):
        super().__init__(**kwargs)
        student_groups = StudentGroupService.get_groups_available_for_student_transfer(student_group)
        choices = ((sg.pk, sg.get_name(branch_details=True)) for sg in student_groups)
        self.fields['student_group'].choices = [('', '-------'), *choices]
        self.helper = FormHelper(self)
        self.helper.form_tag = False

