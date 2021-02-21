from typing import Optional, Type

from grading.constants import CheckingSystemTypes
from courses.models import Assignment, AssignmentSubmissionFormats
from learning.forms import AssignmentSolutionBaseForm, \
    AssignmentSolutionDefaultForm, AssignmentSolutionYandexContestForm
from learning.models import AssignmentComment, StudentAssignment, \
    AssignmentSubmissionTypes
from users.models import User


def get_draft_submission(user: User,
                         student_assignment: StudentAssignment,
                         submission_type,
                         build=False) -> Optional[AssignmentComment]:
    """
    Returns draft submission if it was previously saved in the DB.
    Set `build=True` to return new empty draft instead of `None`.
    This new record is not committed to the DB.
    """
    draft = (AssignmentComment.objects
             .filter(author=user,
                     is_published=False,
                     type=submission_type,
                     student_assignment=student_assignment)
             .last())
    if not draft and build:
        draft = AssignmentComment(student_assignment=student_assignment,
                                  author=user,
                                  type=submission_type,
                                  is_published=False)
    return draft


def get_draft_comment(user: User,
                      student_assignment: StudentAssignment, **kwargs):
    return get_draft_submission(user, student_assignment,
                                AssignmentSubmissionTypes.COMMENT, **kwargs)


def get_draft_solution(user: User,
                       student_assignment: StudentAssignment, **kwargs):
    return get_draft_submission(user, student_assignment,
                                AssignmentSubmissionTypes.SOLUTION, **kwargs)


def get_solution_form(student_assignment: StudentAssignment,
                      **kwargs) -> Optional[AssignmentSolutionBaseForm]:
    assignment = student_assignment.assignment
    submission_format = student_assignment.assignment.submission_type
    if submission_format == AssignmentSubmissionFormats.NO_SUBMIT:
        return None
    elif submission_format == AssignmentSubmissionFormats.EXTERNAL:
        # FIXME: return None
        form = AssignmentSolutionDefaultForm(assignment, **kwargs)
    elif (submission_format == AssignmentSubmissionFormats.CODE_REVIEW
          and assignment.checker_id and assignment.checker.checking_system.type == CheckingSystemTypes.YANDEX):
        form = AssignmentSolutionYandexContestForm(assignment, **kwargs)
    else:
        form = AssignmentSolutionDefaultForm(assignment, **kwargs)
    return form
