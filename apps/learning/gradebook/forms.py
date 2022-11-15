from collections import namedtuple
from typing import Any, Dict, List, Optional

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import BoundField
from django.utils.encoding import force_str
from django.utils.translation import gettext as _

from core.forms import ScoreField
from courses.constants import AssignmentFormat
from courses.models import Assignment
from learning.gradebook.data import GradeBookData
from learning.models import Course, Enrollment, StudentAssignment

__all__ = ('ConflictError', 'BaseGradebookForm', 'AssignmentScore',
           'EnrollmentFinalGrade', 'GradeBookFormFactory', 'GradeBookFilterForm')

from learning.services import StudentGroupService
from learning.services.enrollment_service import update_enrollment_grade
from learning.services.personal_assignment_service import (
    update_personal_assignment_score
)
from learning.settings import AssignmentScoreUpdateSource, EnrollmentGradeUpdateSource
from users.models import User

ConflictError = namedtuple('ConflictError', ['field_name', 'unsaved_value'])


class BaseGradebookForm(forms.Form):
    ASSIGNMENT_SCORE_PREFIX = "sa_"
    FINAL_GRADE_PREFIX = "final_grade_"

    _is_score_readonly: bool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conflicts = False

    def get_final_widget(self, enrollment_id):
        return self[self.FINAL_GRADE_PREFIX + str(enrollment_id)]

    def get_assignment_widget(self, student_assignment_id):
        bound_field = self[self.ASSIGNMENT_SCORE_PREFIX + str(student_assignment_id)]
        if bound_field.errors:
            bound_field.field.widget.attrs["class"] += " __unsaved"
        return bound_field

    def is_widget_enabled(self, student_assignment: StudentAssignment) -> bool:
        return self.is_assignment_widget_enabled(student_assignment,
                                                 self._is_score_readonly)

    @staticmethod
    def is_assignment_widget_enabled(student_assignment: StudentAssignment,
                                     is_readonly: bool) -> bool:
        if is_readonly:
            return False
        assignment = student_assignment.assignment
        # Disallow editing yandex contest results with gradebook form,
        # teachers should use import functionality instead
        if assignment.submission_type == AssignmentFormat.YANDEX_CONTEST:
            return False
        return not assignment.is_online

    def _get_initial_value(self, field_name):
        initial_prefixed_name = self.add_initial_prefix(field_name)
        field = self.fields[field_name]
        hidden_widget = field.hidden_widget()
        try:
            initial_value = field.to_python(
                hidden_widget.value_from_datadict(
                    self.data, self.files, initial_prefixed_name))
        except ValidationError:
            # Always assume data has changed if validation fails.
            initial_value = None
        return initial_value

    def save(self, gradebook: GradeBookData, changed_by: User) -> List[ConflictError]:
        errors = []
        for field_name in self.changed_data:
            if field_name.startswith(self.ASSIGNMENT_SCORE_PREFIX):
                field: AssignmentScore = self.fields[field_name]
                student_assignment = gradebook.get_personal_assignment(field.student_id,
                                                                       field.assignment_id)
                score_old = self._get_initial_value(field_name)
                score_new = self.cleaned_data[field_name]
                updated, _ = update_personal_assignment_score(student_assignment=student_assignment,
                                                              changed_by=changed_by,
                                                              score_old=score_old,
                                                              score_new=score_new,
                                                              source=AssignmentScoreUpdateSource.FORM_GRADEBOOK)
                if not updated:
                    ce = ConflictError(field_name=field_name,
                                       unsaved_value=score_new)
                    errors.append(ce)
            elif field_name.startswith(self.FINAL_GRADE_PREFIX):
                grade_old = self._get_initial_value(field_name)
                grade_new = self.cleaned_data[field_name]
                field: EnrollmentFinalGrade = self.fields[field_name]
                enrollment = gradebook.students[field.student_id]._enrollment
                updated, _ = update_enrollment_grade(enrollment=enrollment,
                                                     old_grade=grade_old, new_grade=grade_new,
                                                     editor=changed_by,
                                                     source=EnrollmentGradeUpdateSource.GRADEBOOK)
                if not updated:
                    ce = ConflictError(field_name=field_name,
                                       unsaved_value=grade_new)
                    errors.append(ce)
        self._conflicts = bool(errors)
        return errors

    def conflicts_on_last_save(self):
        return self._conflicts


class GradeBookFilterForm(forms.Form):
    student_group = forms.TypedChoiceField(
        label=_("Groups"),
        label_suffix='',
        coerce=int,
        empty_value=None,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"})
    )

    def __init__(self, course: Course, **kwargs):
        super().__init__(**kwargs)
        self.fields['student_group'].choices = [
            (None, 'Студенты всех групп'),
            *StudentGroupService.get_choices(course)
        ]

    def is_visible(self) -> bool:
        # Filtering only makes sense if we have at least 3 choices
        # One of them is "All students" others are student groups
        return len(self.fields['student_group'].choices) > 2


class CustomBoundField(BoundField):
    """
    Shows `hidden_initial_value` value provided to field constructor
    on rendering hidden widget.
    """

    def as_hidden(self, attrs=None, **kwargs):
        """
        Returns a string of HTML for representing this as an <input type="hidden">.
        """
        widget = self.field.hidden_widget()
        return force_str(widget.render(self.html_initial_name,
                                       self.field.hidden_initial_value,
                                       attrs=attrs))


class AssignmentScore(ScoreField):
    def __init__(self, assignment: Assignment,
                 student_assignment: StudentAssignment) -> None:
        score = student_assignment.score
        widget = forms.TextInput(attrs={
            'class': 'cell __assignment __input',
            'max': assignment.maximum_score,
            'initial': score if score is not None else ""
        })
        super().__init__(min_value=0,
                         max_value=assignment.maximum_score,
                         required=False,
                         show_hidden_initial=True,
                         widget=widget)
        # Used to simplify `form.save()` method
        self.student_assignment_id = student_assignment.id
        self.student_id = student_assignment.student_id
        self.assignment_id = student_assignment.assignment.id
        self.submission_score = score
        self.hidden_initial_value = self.submission_score

    def get_bound_field(self, form, field_name):
        """
        Uses custom BoundField instance that will be used when accessing the
        form field in a template.
        """
        return CustomBoundField(form, self, field_name)


class EnrollmentFinalGrade(forms.ChoiceField):
    def __init__(self, student, course, is_readonly: bool = False):
        widget = forms.Select(attrs={
            'initial': student.final_grade,
            'disabled': is_readonly
        })
        super().__init__(choices=course.grade_choices,
                         required=False,
                         show_hidden_initial=True,
                         widget=widget)
        # Used to simplify `form.save()` method
        self.student_id = student.id
        self.enrollment_id = student.enrollment_id
        self.final_grade = student.final_grade
        self.hidden_initial_value = self.final_grade

    def get_bound_field(self, form, field_name):
        """
        Uses custom BoundField instance that will be used when accessing the
        form field in a template.
        """
        return CustomBoundField(form, self, field_name)


class GradeBookFormFactory:
    @classmethod
    def build_form_class(cls, gradebook: GradeBookData, *,
                         is_readonly: bool = True):
        """
        Creates new form.Form subclass with students scores for
        each offline assignment (which student can't pass on this site) and
        students final grades for provided course.
        Internally each field of the form uses `show_hidden_initial` feature,
        but stores value provided to field constructor
        (see `CustomBoundField`) instead of the value provided to the form.
        """
        fields: Dict[str, forms.Field] = {}
        max_number = settings.DATA_UPLOAD_MAX_NUMBER_FIELDS
        is_number_of_fields_exceeded = (gradebook.number_of_fields > max_number)
        is_assignment_score_readonly = (is_readonly or
                                        len(gradebook.students) > 100 or
                                        is_number_of_fields_exceeded)

        for student_progress in gradebook.student_assignments:
            for sa in student_progress:
                # Student has no record for tracking progress after withdrawal
                if not sa:
                    continue
                assignment = sa.assignment
                if BaseGradebookForm.is_assignment_widget_enabled(sa, is_assignment_score_readonly):
                    k = BaseGradebookForm.ASSIGNMENT_SCORE_PREFIX + str(sa.id)
                    fields[k] = AssignmentScore(assignment, sa)

        for gs in gradebook.students.values():
            k = BaseGradebookForm.FINAL_GRADE_PREFIX + str(gs.enrollment_id)
            fields[k] = EnrollmentFinalGrade(gs, gradebook.course, is_readonly)
        cls_dict: Dict[str, Any] = fields
        cls_dict["_course"] = gradebook.course
        cls_dict["_is_score_readonly"] = is_assignment_score_readonly
        cls_dict["is_readonly"] = is_readonly
        return type("GradebookForm", (BaseGradebookForm,), cls_dict)

    @classmethod
    def transform_to_initial(cls, gradebook: GradeBookData):
        initial = {}
        for student_progress in gradebook.student_assignments:
            for student_assignment in student_progress:
                # Student has no record for tracking progress after withdrawal
                if not student_assignment:
                    continue
                assignment = student_assignment.assignment
                if not assignment.is_online:
                    k = BaseGradebookForm.ASSIGNMENT_SCORE_PREFIX + str(student_assignment.id)
                    initial[k] = student_assignment.score
        for gs in gradebook.students.values():
            k = BaseGradebookForm.FINAL_GRADE_PREFIX + str(gs.enrollment_id)
            initial[k] = gs.final_grade
        return initial
