import csv
import logging
from decimal import Decimal
from typing import IO, Callable, Dict, List, Optional

from rest_framework import serializers

from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.translation import gettext_lazy as _

from core.forms import ScoreField
from core.utils import normalize_yandex_login
from courses.constants import AssignmentFormat
from courses.models import Assignment, Course
from grading.api.yandex_contest import (
    ProblemStatus, YandexContestAPI, yandex_contest_scoreboard_iterator
)
from grading.models import Checker
from grading.utils import YandexContestScoreSource
from learning.models import Enrollment, StudentAssignment
from learning.services.enrollment_service import update_enrollment_grade
from learning.services.personal_assignment_service import (
    update_personal_assignment_score
)
from learning.settings import AssignmentScoreUpdateSource, EnrollmentGradeUpdateSource, GradeTypes
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


def assignment_import_scores_from_yandex_contest(*, checker: Checker,
                                                 assignment: Assignment,
                                                 triggered_by: User) -> None:
    contest_id = checker.settings['contest_id']

    # Note: There is no API call to check that yandex contest problem max
    # score is synchronized with the assignment max score.
    enrolled_students = (Enrollment.active
                         .filter(course_id=assignment.course_id)
                         .select_related('student_profile__user__yandex_data'))
    students = {}
    for e in enrolled_students:
        yandex_login = normalize_yandex_login(e.student_profile.user.yandex_login)
        if yandex_login is not None:
            students[yandex_login] = e.student_profile.user
    student_assignments = StudentAssignment.objects.filter(assignment=assignment).order_by()
    student_assignments = {s.student_id: s for s in student_assignments}

    access_token = checker.checking_system.settings['access_token']
    client = YandexContestAPI(access_token=access_token, refresh_token=access_token)
    for participant_results in yandex_contest_scoreboard_iterator(client, contest_id):
        if participant_results.yandex_login not in students:
            continue
        student = students[participant_results.yandex_login]
        # Student could leave the course or is on academic leave
        if student.pk not in student_assignments:
            continue
        student_assignment = student_assignments[student.pk]
        assert student_assignment.assignment_id == assignment.pk
        student_assignment.assignment = assignment
        student_assignment.student = student

        score_old = student_assignment.score
        score_input = checker.settings.get('score_input')
        if score_input == YandexContestScoreSource.PROBLEM.value:
            problem_alias = checker.settings['problem_id']
            gen = (pr for pr in participant_results.problems if pr.problem_alias == problem_alias)
            problem_results = next(gen, None)
            if not problem_results:
                raise serializers.ParseError("Problem was not found")
            if problem_results.status == ProblemStatus.NOT_SUBMITTED and score_old is None:
                continue
            score_new = problem_results.score
        elif score_input == YandexContestScoreSource.CONTEST.value:
            score_new = participant_results.score_total
        else:
            raise serializers.ParseError("Unknown score input")

        update_personal_assignment_score(student_assignment=student_assignment,
                                         changed_by=triggered_by,
                                         score_old=score_old,
                                         score_new=score_new,
                                         source=AssignmentScoreUpdateSource.API_YANDEX_CONTEST)


def assignment_import_scores_from_csv(csv_file: IO,
                                      required_headers: List[CSVColumnName],
                                      lookup_column_name: CSVColumnName,
                                      student_assignments: Dict[CSVColumnValue, StudentAssignment],
                                      changed_by: User,
                                      audit_log_source: AssignmentScoreUpdateSource,
                                      transform_value: Optional[Callable[[CSVColumnValue], CSVColumnValue]] = None):
    # Remove BOM by using 'utf-8-sig'
    f = (bs.decode("utf-8-sig") for bs in csv_file)
    reader = csv.DictReader(f)
    reader.fieldnames = [name.lower() for name in reader.fieldnames]
    errors = _validate_headers(reader, required_headers)
    if errors:
        raise ValidationError("<br>".join(errors))

    logger.info(f"Start processing csv")

    found = 0
    imported = 0
    for row_number, row in enumerate(reader, start=1):
        lookup_value = row[lookup_column_name].strip()
        if transform_value:
            lookup_value = transform_value(lookup_value)
        if lookup_value not in student_assignments:
            continue
        found += 1
        student_assignment = student_assignments[lookup_value]
        try:
            score_new = _score_to_python(row["score"])
        except ValidationError as e:
            logger.debug(e.message)
            raise ValidationError(f'Row {row_number}: {e.message}',
                                  code='invalid_score')
            # TODO: collect errors instead?
        try:
            update_personal_assignment_score(student_assignment=student_assignment,
                                             changed_by=changed_by,
                                             score_old=student_assignment.score,
                                             score_new=score_new,
                                             source=audit_log_source)
            logger.info(f"{score_new} points has written to the personal assignment {student_assignment.pk}")
        except ValidationError:
            logger.info(f"Invalid score {score_new} on line {row_number}")
            continue
        imported += 1
    return found, imported


def enrollment_import_grades_from_csv(csv_file: IO,
                                      course: Course,
                                      required_headers: List[CSVColumnName],
                                      lookup_column_name: CSVColumnName,
                                      enrollments: Dict[CSVColumnValue, Enrollment],
                                      changed_by: User,
                                      grade_log_source: EnrollmentGradeUpdateSource,
                                      transform_value: Optional[Callable[[CSVColumnValue], CSVColumnValue]] = None):
    # Remove BOM by using 'utf-8-sig'
    f = (bs.decode("utf-8-sig") for bs in csv_file)
    reader = csv.DictReader(f)
    reader.fieldnames = [name.lower() for name in reader.fieldnames]
    errors = _validate_headers(reader, required_headers)
    if errors:
        raise ValidationError("<br>".join(errors))

    logger.info(f"Start processing csv")

    found = 0
    imported = 0
    errors = []
    for row_number, row in enumerate(reader, start=1):
        raw_lookup_value = row[lookup_column_name].strip()
        lookup_value = raw_lookup_value
        if transform_value:
            lookup_value = transform_value(raw_lookup_value)
        if lookup_value not in enrollments:
            error_msg = f'Строка {row_number}: студент с идентификатором "{raw_lookup_value}" не найден.'
            logger.warning(error_msg)
            errors.append(error_msg)
            continue
        found += 1
        enrollment = enrollments[lookup_value]
        try:
            grade = GradeTypes.get_choice_from_russian_label(row['итоговая оценка'])
            grade_tuple = (grade.value, grade.label)
            if not GradeTypes.is_suitable_for_grading_system(grade_tuple, course.grading_system.value):
                raise ValidationError(f"оценка '{row['итоговая оценка']}' не подходит для системы оценивая этого курса"
                                      f", идентификатор студента '{raw_lookup_value}'.")
        except (KeyError, ValidationError) as e:
            logger.warning(e)
            errors.append(f'Строка {row_number}: {e.message if isinstance(e, ValidationError) else e}')
            continue
        try:
            is_success, _ = update_enrollment_grade(enrollment,
                                                    editor=changed_by,
                                                    old_grade=enrollment.grade,
                                                    new_grade=grade.value,
                                                    source=grade_log_source)
            if not is_success:
                error_msg = f"Строка {row_number}: обновление не произошла из-за конфликта с внешним изменением."
                errors.append(error_msg)
                logger.warning(error_msg)
            logger.info(f"Enrollment grade has been updated from {enrollment.grade}"
                        f" to {grade.value} for {enrollment}")
        except PermissionDenied:
            logger.error(f"You have no permission to change enrollment grade via csv-import.")
            raise
        except ValidationError as ve:
            error_msg = f"Строка {row_number}: некорректная оценка '{row['итоговая оценка']}'" \
                        f" для студента с идентификатором '{raw_lookup_value}' ({ve.message})."
            logger.error(error_msg)
            errors.append(error_msg)
            continue
        except Exception as e:
            logger.error(e)
            errors.append(str(e))
            continue
        imported += 1
    return found, imported, errors


def _validate_headers(reader: csv.DictReader,
                      required_headers: List[CSVColumnName]):
    headers = reader.fieldnames
    errors = []
    for header in required_headers:
        if header not in headers:
            errors.append(_("Header '{}' not found").format(header))
    return errors


_score_field = ScoreField()


def _score_to_python(raw_value: str) -> Optional[Decimal]:
    try:
        cleaned_value = _score_field.clean(raw_value)
    except ValidationError:
        msg = _("Invalid score format '{}'").format(raw_value)
        raise ValidationError(msg, code="invalid_score")
    return cleaned_value
