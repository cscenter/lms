import csv
import logging

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import ugettext_lazy as _

from learning.forms import AssignmentScoreForm
from learning.models import Enrollment, StudentAssignment

__all__ = ('AssignmentGradesImport',)

logger = logging.getLogger(__name__)


class AssignmentGradesImport:
    def __init__(self, assignment, csv_file: UploadedFile,
                 lookup_field, request=None):
        self.assignment = assignment
        # Remove BOM by using 'utf-8-sig'
        f = (bs.decode("utf-8-sig") for bs in csv_file)
        self.reader = csv.DictReader(f)
        self.lookup_field = lookup_field

    def validate_headers(self):
        headers = self.reader.fieldnames
        errors = []
        for header in [self.lookup_field, "total"]:
            if header not in headers:
                errors.append(f"Header `{header}` not found")
        return errors

    def process(self):
        errors = self.validate_headers()
        if errors:
            raise ValidationError("<br>".join(errors))
        msg = f"Start processing results for assignment {self.assignment.id}"
        logger.debug(msg)

        qs = (Enrollment.active
              .filter(course_id=self.assignment.course_id)
              .only("student_id",
                    f"student__{self.lookup_field}"))
        active_students = {}
        for s in qs.iterator():
            lookup_field_value = getattr(s.student, self.lookup_field)
            active_students[str(lookup_field_value)] = s.student_id

        total = 0
        success = 0
        for row in self.reader:
            total += 1
            try:
                lookup_field_value, score = self.clean(row)
                student_id = active_students.get(lookup_field_value, None)
                if student_id:
                    updated = self.update_score(student_id, score)
                    if not updated:
                        msg = (f"Student with {self.lookup_field} = "
                               f"{lookup_field_value} enrolled "
                               f"but doesn't have an assignment.")
                        logger.debug(msg)
                    success += int(updated)
            except ValidationError as e:
                logger.debug(e.message)
        return total, success

    def clean(self, row):
        lookup_field_value = row[self.lookup_field].strip()
        try:
            score_field = AssignmentScoreForm.declared_fields['score']
            score = score_field.to_python(row["total"])
        except ValidationError:
            msg = _("Can't convert points for user '{}'").format(
                lookup_field_value)
            raise ValidationError(msg, code='invalid_score_value')
        if score > self.assignment.maximum_score:
            msg = _("Score is greater than max grade for user '{}'").format(
                lookup_field_value)
            raise ValidationError(msg, code='invalid_score_value')
        return lookup_field_value, score

    def update_score(self, student_id, score):
        assignment_id = self.assignment.pk
        updated = (StudentAssignment.objects
                   .filter(assignment__id=assignment_id,
                           student_id=student_id)
                   .update(score=score))
        if not updated:
            return False
        logger.debug(f"{score} points has written to student {student_id}")
        return True
