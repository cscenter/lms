import csv
import logging
from decimal import Decimal
from typing import IO, Callable, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from courses.constants import AssignmentFormat
from courses.models import Assignment
from grading.api.yandex_contest import (
    ProblemStatus, YandexContestAPI, yandex_contest_scoreboard_iterator
)
from grading.models import Checker
from learning.forms import AssignmentScoreForm
from learning.models import Enrollment, StudentAssignment
from learning.services.personal_assignment_service import (
    update_personal_assignment_score
)
from learning.settings import AssignmentScoreUpdateSource
from users.models import User

logger = logging.getLogger(__name__)

CSVColumnName = str
CSVColumnValue = str


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


def get_course_students(course_id) -> Dict[CSVColumnValue, int]:
    enrollments = (Enrollment.active
                   .filter(course_id=course_id)
                   .only("student_id", "id"))
    return {str(e.id): e.student_id for e in enrollments}


def get_course_students_by_stepik_id(course_id) -> Dict[CSVColumnValue, int]:
    """
    Returns course students that provided stepik ID in their account.
    """
    enrollments = (Enrollment.active
                   .filter(course_id=course_id)
                   .only("student_id", "student__stepic_id"))
    enrolled_students = {}
    for enrollment in enrollments.iterator():
        stepik_id = enrollment.student.stepic_id
        if stepik_id:
            enrolled_students[str(stepik_id)] = enrollment.student_id
    return enrolled_students


def get_course_students_by_yandex_login(course_id) -> Dict[CSVColumnValue, int]:
    """
    Returns course students that provided yandex login in their account.
    """
    enrollments = (Enrollment.active
                   .filter(course_id=course_id)
                   .only("student_id", "student__yandex_login_normalized"))
    enrolled_students = {}
    for enrollment in enrollments.iterator():
        yandex_login = enrollment.student.yandex_login_normalized
        if yandex_login:
            enrolled_students[str(yandex_login)] = enrollment.student_id
    return enrolled_students


def assignment_import_scores_from_csv(assignment: Assignment,
                                      csv_file: IO,
                                      enrolled_students: Dict[CSVColumnValue, int],
                                      required_headers: List[CSVColumnName],
                                      lookup_column_name: str,
                                      transform: Optional[Callable[[str], str]] = None):
    # Remove BOM by using 'utf-8-sig'
    f = (bs.decode("utf-8-sig") for bs in csv_file)
    reader = csv.DictReader(f)
    reader.fieldnames = [name.lower() for name in reader.fieldnames]
    errors = _validate_headers(reader, required_headers)
    if errors:
        raise ValidationError("<br>".join(errors))

    logger.debug(f"Start processing results for assignment {assignment.id}")

    found = 0
    imported = 0
    maximum_score = assignment.maximum_score

    for row_number, row in enumerate(reader, start=1):
        lookup_column_value = row[lookup_column_name].strip()
        if transform:
            lookup_column_value = transform(lookup_column_value)
        student_id = enrolled_students.get(lookup_column_value, None)
        if not student_id:
            continue
        found += 1
        try:
            score = _score_to_python(row["score"], maximum_score)
        except ValidationError as e:
            logger.debug(e.message)
            raise ValidationError(f'Row {row_number}: {e.message}',
                                  code='invalid_score')
            # TODO: collect errors instead?
        # Try to update student assignment score
        updated = (StudentAssignment.objects
                   .filter(assignment=assignment,
                           student_id=student_id)
                   .update(score=score))
        if updated:
            msg = f"{score} points has written to student {student_id}"
        else:
            msg = (f"Student with {lookup_column_name} = {lookup_column_value} "
                   f"is enrolled but doesn't have personal assignment.")
        logger.debug(msg)
        imported += int(updated)
    return found, imported


def _validate_headers(reader: csv.DictReader,
                      required_headers: List[CSVColumnName]):
    headers = reader.fieldnames
    errors = []
    for header in required_headers:
        if header not in headers:
            errors.append(_("Header '{}' not found").format(header))
    return errors


def _score_to_python(raw_value: str, maximum_score) -> Optional[Decimal]:
    score_field = AssignmentScoreForm.declared_fields['score']
    try:
        cleaned_value = score_field.clean(raw_value)
    except ValidationError:
        msg = _("Invalid score format '{}'").format(raw_value)
        raise ValidationError(msg, code="invalid_score")
    if cleaned_value > maximum_score:
        msg = _("Score '{}' is greater than the maximum score '{}'").format(
            raw_value, maximum_score)
        raise ValidationError(msg, code='score_overflow')
    return cleaned_value
