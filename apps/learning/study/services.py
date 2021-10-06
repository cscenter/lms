from typing import Optional

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.forms import ModelForm

from core.urls import reverse
from courses.constants import AssignmentFormat
from grading.constants import CheckingSystemTypes
from grading.services import CheckerService
from learning.forms import (
    AssignmentSolutionBaseForm, AssignmentSolutionDefaultForm,
    AssignmentSolutionYandexContestForm
)
from learning.models import AssignmentComment, StudentAssignment
from learning.services import (
    create_assignment_solution, create_assignment_solution_and_check
)
from users.models import User


def get_solution_form(student_assignment: StudentAssignment,
                      data=None, files=None) -> Optional[AssignmentSolutionBaseForm]:
    assignment = student_assignment.assignment
    assignment_format = assignment.submission_type
    if assignment_format == AssignmentFormat.NO_SUBMIT:
        return None
    elif assignment_format == AssignmentFormat.YANDEX_CONTEST:
        return None
    elif assignment_format == AssignmentFormat.EXTERNAL:
        # FIXME: return None
        form = AssignmentSolutionDefaultForm(assignment, data=data, files=files)
    elif (assignment_format == AssignmentFormat.CODE_REVIEW
          and assignment.checker_id and assignment.checker.checking_system.type == CheckingSystemTypes.YANDEX):
        form = AssignmentSolutionYandexContestForm(assignment, data=data, files=files)
    else:
        form = AssignmentSolutionDefaultForm(assignment, data=data, files=files)
    if form:
        add_solution_url = reverse('study:assignment_solution_create',
                                   kwargs={'pk': student_assignment.pk})
        form.helper.form_action = add_solution_url
    return form


def save_solution_form(*, form: AssignmentSolutionBaseForm,
                       personal_assignment: StudentAssignment,
                       created_by: User) -> AssignmentComment:
    print(form.cleaned_data)
    if isinstance(form, AssignmentSolutionDefaultForm):
        # TODO: здесь достаём всё что необходимо из формы
        solution_data = {
            "message": form.cleaned_data['text'],
            "attachment": form.cleaned_data['attached_file'],
            "execution_time": form.cleaned_data['execution_time'],
        }
        submission = create_assignment_solution(
            personal_assignment=personal_assignment,
            created_by=created_by,
            **solution_data)
    elif isinstance(form, AssignmentSolutionYandexContestForm):
        solution_data = {
            "attachment": form.cleaned_data['attached_file'],
            "execution_time": form.cleaned_data['execution_time'],
        }
        checker_submission_settings = {
            "compiler": form.cleaned_data['compiler'],
        }
        submission = create_assignment_solution_and_check(
            personal_assignment=personal_assignment,
            created_by=created_by,
            settings=checker_submission_settings,
            **solution_data)
    else:
        raise ValueError(f"{form.__class__} is not supported")
    return submission
