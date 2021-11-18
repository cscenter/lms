from django.core.exceptions import ValidationError

from courses.constants import AssignmentFormat
from courses.models import Assignment
from grading.api.yandex_contest import (
    ProblemStatus, YandexContestAPI, yandex_contest_scoreboard_iterator
)
from grading.models import Checker
from learning.models import Enrollment, StudentAssignment
from learning.services.personal_assignment_service import (
    update_personal_assignment_score
)
from learning.settings import AssignmentScoreUpdateSource
from users.models import User


def get_assignment_checker(assignment: Assignment) -> Checker:
    if assignment.submission_type != AssignmentFormat.YANDEX_CONTEST:
        raise ValidationError("Wrong assignment format", code="invalid")
    if not assignment.checker_id:
        raise ValidationError("Checker is not defined", code="malformed")
    return assignment.checker


def assignment_import_scores_from_yandex_contest(*, client: YandexContestAPI,
                                                 assignment: Assignment,
                                                 triggered_by: User) -> None:
    checker = get_assignment_checker(assignment)
    contest_id = checker.settings['contest_id']
    problem_alias = checker.settings['problem_id']

    # There is no API call to check that yandex contest problem max score is
    # synchronized with the assignment max score.
    enrolled_students = (Enrollment.active
                         .filter(course_id=assignment.course_id)
                         .exclude(student_profile__user__yandex_login_normalized='')
                         .select_related('student_profile__user')
                         .only('student_profile__user'))
    students = {e.student_profile.user.yandex_login_normalized: e.student_profile.user
                for e in enrolled_students}
    student_assignments = StudentAssignment.objects.filter(assignment=assignment).order_by()
    student_assignments = {s.student_id: s for s in student_assignments}
    for participant_results in yandex_contest_scoreboard_iterator(client, contest_id):
        if participant_results.yandex_login not in students:
            continue
        student = students[participant_results.yandex_login]
        gen = (pr for pr in participant_results.problems if pr.problem_alias == problem_alias)
        problem_results = next(gen, None)
        if not problem_results:
            raise ValidationError("Problem was not found", code="malformed")
        if problem_results.status == ProblemStatus.NOT_SUBMITTED:
            continue
        # Student could left the course or is on academic leave
        if student.pk in student_assignments:
            student_assignment = student_assignments[student.pk]
            assert student_assignment.assignment_id == assignment.pk
            student_assignment.assignment = assignment
            student_assignment.student = student
            update_personal_assignment_score(student_assignment=student_assignment,
                                             changed_by=triggered_by,
                                             score_old=student_assignment.score,
                                             score_new=problem_results.score,
                                             source=AssignmentScoreUpdateSource.API_YANDEX_CONTEST)
