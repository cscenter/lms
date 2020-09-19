import csv
import logging
from decimal import Decimal
from typing import Optional, List, IO, Dict

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

from courses.models import Assignment
from learning.forms import AssignmentScoreForm
from learning.models import Enrollment, StudentAssignment

__all__ = ('import_assignment_scores',)

logger = logging.getLogger(__name__)

CSVColumnName = str
CSVColumnValue = str


def validate_headers(reader: csv.DictReader,
                     required_headers: List[CSVColumnName]):
    headers = reader.fieldnames
    errors = []
    for header in required_headers:
        if header not in headers:
            errors.append(f"Header `{header}` not found")
    return errors


def get_course_students(course_id) -> Dict[CSVColumnValue, int]:
    enrollments = (Enrollment.active
                   .filter(course_id=course_id)
                   .only("student_id", "id"))
    return {str(e.id): e.student_id for e in enrollments}


def get_course_students_by_stepik_id(course_id) -> Dict[CSVColumnValue, int]:
    """
    Returns course students that provided stepik ID in their accounts.
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
    Returns course students that provided yandex login in their accounts.
    """
    enrollments = (Enrollment.active
                   .filter(course_id=course_id)
                   .only("student_id", "student__yandex_login"))
    enrolled_students = {}
    for enrollment in enrollments.iterator():
        yandex_login = enrollment.student.yandex_login
        if yandex_login:
            enrolled_students[str(yandex_login)] = enrollment.student_id
    return enrolled_students


def import_assignment_scores(assignment: Assignment,
                             csv_file: IO,
                             enrolled_students: Dict[CSVColumnValue, int],
                             required_headers: List[CSVColumnName],
                             lookup_column_name: str):
    # Remove BOM by using 'utf-8-sig'
    f = (bs.decode("utf-8-sig") for bs in csv_file)
    reader = csv.DictReader(f)
    errors = validate_headers(reader, required_headers)
    if errors:
        raise ValidationError("<br>".join(errors))

    logger.debug(f"Start processing results for assignment {assignment.id}")

    found = 0
    imported = 0
    maximum_score = assignment.maximum_score
    for row_number, row in enumerate(reader, start=1):
        lookup_column_value = row[lookup_column_name].strip()
        student_id = enrolled_students.get(lookup_column_value, None)
        if not student_id:
            continue
        found += 1
        try:
            score = score_to_python(row["score"], maximum_score)
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


def score_to_python(raw_value: str, maximum_score) -> Optional[Decimal]:
    score_field = AssignmentScoreForm.declared_fields['score']
    try:
        cleaned_value = score_field.clean(raw_value)
    except ValidationError:
        msg = _("Invalid score format '{}'").format(raw_value)
        raise ValidationError(msg, code="invalid_score")
    if cleaned_value > maximum_score:
        msg = _("Score '{}' is greater than the maximum score {}").format(
            raw_value, maximum_score)
        raise ValidationError(msg, code='score_overflow')
    return cleaned_value
