from django.core.exceptions import ValidationError

from courses.constants import AssignmentFormat
from courses.models import Assignment
from grading.api.yandex_contest import ProblemStatus, YandexContestAPI
from grading.models import Checker
from grading.services import yandex_contest_scoreboard_iterator
from learning.models import Enrollment
from learning.services import update_personal_assignment_score


def get_assignment_checker(assignment: Assignment) -> Checker:
    if assignment.submission_type != AssignmentFormat.YANDEX_CONTEST:
        raise ValidationError("Wrong assignment format", code="invalid")
    if not assignment.checker_id:
        raise ValidationError("Checker is not defined", code="malformed")
    return assignment.checker


def assignment_import_scores_from_yandex_contest(client: YandexContestAPI,
                                                 assignment: Assignment) -> None:
    checker = get_assignment_checker(assignment)
    contest_id = checker.settings['contest_id']
    problem_alias = checker.settings['problem_id']

    # There is no API call to check that yandex contest problem max score is
    # synchronized with the assignment max score.
    enrolled_students = (Enrollment.active
                         .filter(course_id=assignment.course_id)
                         .exclude(student_profile__user__yandex_login='')
                         .values_list('student_profile__user__yandex_login', 'student_profile__user_id'))
    yandex_logins = {yandex_login: user_id for yandex_login, user_id in enrolled_students}
    for participant_results in yandex_contest_scoreboard_iterator(client, contest_id):
        if participant_results.yandex_login not in yandex_logins:
            continue
        gen = (pr for pr in participant_results.problems if pr.problem_alias == problem_alias)
        problem_results = next(gen, None)
        if not problem_results:
            raise ValidationError("Problem was not found", code="malformed")
        if problem_results.status == ProblemStatus.NOT_SUBMITTED:
            continue
        user_id = yandex_logins[participant_results.yandex_login]
        update_personal_assignment_score(assignment=assignment, student=user_id,
                                         score=problem_results.score)
