from collections import namedtuple
from typing import List

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import BoundField
from django.utils.encoding import force_str

from core.forms import GradeField
from learning.gradebook.utils import recalculate_course_grading_system
from learning.gradebook.data import GradeBookData
from learning.models import StudentAssignment, Enrollment
from learning.settings import GradeTypes

__all__ = ('ConflictError', 'BaseGradebookForm', 'AssignmentScore',
           'EnrollmentFinalGrade', 'GradeBookFormFactory')

ConflictError = namedtuple('ConflictError', ['field_name', 'unsaved_value'])


class BaseGradebookForm(forms.Form):
    GRADE_PREFIX = "sa_"
    FINAL_GRADE_PREFIX = "final_grade_"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conflicts = False

    def get_final_widget(self, enrollment_id):
        return self[self.FINAL_GRADE_PREFIX + str(enrollment_id)]

    def get_assignment_widget(self, student_assignment_id):
        bound_field = self[self.GRADE_PREFIX + str(student_assignment_id)]
        if bound_field.errors:
            bound_field.field.widget.attrs["class"] += " __unsaved"
        return bound_field

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

    def save(self) -> List[ConflictError]:
        final_grade_updated = False
        errors = []
        for field_name in self.changed_data:
            if field_name.startswith(self.GRADE_PREFIX):
                current_value = self._get_initial_value(field_name)
                new_value = self.cleaned_data[field_name]
                field = self.fields[field_name]
                # This is not a conflict situation when new value already in db
                updated = (StudentAssignment.objects
                           .filter(pk=field.student_assignment_id)
                           .filter(Q(score=current_value) | Q(score=new_value))
                           .update(score=new_value))
                if not updated:
                    ce = ConflictError(field_name=field_name,
                                       unsaved_value=new_value)
                    errors.append(ce)
            elif field_name.startswith(self.FINAL_GRADE_PREFIX):
                current_value = self._get_initial_value(field_name)
                new_value = self.cleaned_data[field_name]
                field = self.fields[field_name]
                updated = (Enrollment.objects
                           .filter(pk=field.enrollment_id)
                           .filter(Q(grade=current_value) | Q(grade=new_value))
                           .update(grade=new_value))
                if not updated:
                    ce = ConflictError(field_name=field_name,
                                       unsaved_value=new_value)
                    errors.append(ce)
                else:
                    final_grade_updated = True
        if final_grade_updated:
            recalculate_course_grading_system(self._course)
        self._conflicts = bool(errors)
        return errors

    def conflicts_on_last_save(self):
        return self._conflicts


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


class AssignmentScore(GradeField):
    def __init__(self, assignment, submission):
        score = submission.score
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
        self.student_assignment_id = submission.id
        self.submission_score = score
        self.hidden_initial_value = self.submission_score

    def get_bound_field(self, form, field_name):
        """
        Uses custom BoundField instance that will be used when accessing the
        form field in a template.
        """
        return CustomBoundField(form, self, field_name)


class EnrollmentFinalGrade(forms.ChoiceField):
    def __init__(self, student, course):
        widget = forms.Select(attrs={
            'initial': student.final_grade
        })
        super().__init__(choices=course.grade_choices,
                         required=False,
                         show_hidden_initial=True,
                         widget=widget)
        # Used to simplify `form.save()` method
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
    def build_form_class(cls, gradebook: GradeBookData):
        """
        Creates new form.Form subclass with students scores for
        each offline assignment (which student can't pass on this site) and
        students final grades for provided course.
        Internally each field of the form uses `show_hidden_initial` feature,
        but stores value provided to field constructor
        (see `CustomBoundField`) instead of the value provided to the form.
        """
        cls_dict = fields = {}
        for student_assignments in gradebook.submissions:
            for sa in student_assignments:
                # Student have no submissions after withdrawal
                if not sa:
                    continue
                assignment = sa.assignment
                if not assignment.is_online:
                    k = BaseGradebookForm.GRADE_PREFIX + str(sa.id)
                    fields[k] = AssignmentScore(assignment, sa)

        for s in gradebook.students.values():
            k = BaseGradebookForm.FINAL_GRADE_PREFIX + str(s.enrollment_id)
            fields[k] = EnrollmentFinalGrade(s, gradebook.course)
        cls_dict["_course"] = gradebook.course
        return type("GradebookForm", (BaseGradebookForm,), cls_dict)

    @classmethod
    def transform_to_initial(cls, gradebook: GradeBookData):
        initial = {}
        for student_submissions in gradebook.submissions:
            for submission in student_submissions:
                # Student have no submissions after withdrawal
                if not submission:
                    continue
                assignment = submission.assignment
                if not assignment.is_online:
                    k = BaseGradebookForm.GRADE_PREFIX + str(submission.id)
                    initial[k] = submission.score
        for s in gradebook.students.values():
            k = BaseGradebookForm.FINAL_GRADE_PREFIX + str(s.enrollment_id)
            initial[k] = s.final_grade
        return initial
