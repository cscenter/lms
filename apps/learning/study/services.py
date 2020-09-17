from typing import Optional, Type

from courses.models import Assignment, AssignmentSubmissionFormats
from learning.forms import AssignmentSolutionBaseForm, \
    AssignmentSolutionDefaultForm
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


def get_draft_comment(user: User, student_assignment: StudentAssignment):
    return get_draft_submission(user, student_assignment,
                                AssignmentSubmissionTypes.COMMENT)


def get_draft_solution(user: User, student_assignment: StudentAssignment):
    return get_draft_submission(user, student_assignment,
                                AssignmentSubmissionTypes.SOLUTION)


def get_solution_form(student_assignment: StudentAssignment,
                      **kwargs) -> Optional[AssignmentSolutionBaseForm]:
    course = student_assignment.assignment.course
    submission_format = student_assignment.assignment.submission_type
    if submission_format == AssignmentSubmissionFormats.EXTERNAL:
        # FIXME: return None
        form = AssignmentSolutionDefaultForm(course, **kwargs)
    else:
        form = AssignmentSolutionDefaultForm(course, **kwargs)
    return form
