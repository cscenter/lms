from typing import Optional

from courses.constants import AssignmentFormat
from grading.constants import CheckingSystemTypes
from learning.forms import (
    AssignmentSolutionBaseForm, AssignmentSolutionDefaultForm,
    AssignmentSolutionYandexContestForm
)
from learning.models import (
    StudentAssignment
)


def get_solution_form(student_assignment: StudentAssignment,
                      **kwargs) -> Optional[AssignmentSolutionBaseForm]:
    assignment = student_assignment.assignment
    submission_format = student_assignment.assignment.submission_type
    if submission_format == AssignmentFormat.NO_SUBMIT:
        return None
    elif submission_format == AssignmentFormat.YANDEX_CONTEST:
        return None
    elif submission_format == AssignmentFormat.EXTERNAL:
        # FIXME: return None
        form = AssignmentSolutionDefaultForm(assignment, **kwargs)
    elif (submission_format == AssignmentFormat.CODE_REVIEW
          and assignment.checker_id and assignment.checker.checking_system.type == CheckingSystemTypes.YANDEX):
        form = AssignmentSolutionYandexContestForm(assignment, **kwargs)
    else:
        form = AssignmentSolutionDefaultForm(assignment, **kwargs)
    return form
