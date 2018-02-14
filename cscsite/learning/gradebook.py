import logging
from typing import List

import numpy as np
import unicodecsv
from collections import OrderedDict, namedtuple
from math import ceil

from django import forms
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db.models import Q
from django.forms import BoundField
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from learning.forms import GradeField, AssignmentGradeForm
from learning.models import StudentAssignment, Enrollment, Assignment, \
    CourseOffering
from learning.settings import GRADES
from users.models import CSCUser

logger = logging.getLogger(__name__)


class StudentMeta:
    def __init__(self, enrollment: Enrollment, index: int):
        self._enrollment = enrollment
        # Will be filled later based on assignments data
        self.total_score = None
        self.index = index

    @property
    def id(self):
        return self._enrollment.student_id

    @property
    def enrollment_id(self):
        return self._enrollment.pk

    @property
    def final_grade(self):
        return self._enrollment.grade

    @property
    def first_name(self):
        return self._enrollment.student.first_name

    @property
    def last_name(self):
        return self._enrollment.student.last_name

    @property
    def patronymic(self):
        return self._enrollment.student.patronymic

    @property
    def username(self):
        return self._enrollment.student.username

    @property
    def yandex_id(self):
        return self._enrollment.student.yandex_id

    def get_absolute_url(self):
        return self._enrollment.student.get_absolute_url()

    def get_abbreviated_name(self):
        return self._enrollment.student.get_abbreviated_name()

    def get_abbreviated_short_name(self):
        return self._enrollment.student.get_abbreviated_short_name()

    @property
    def final_grade_display(self):
        return GRADES[self.final_grade]


class SubmissionData:
    def __init__(self, submission: StudentAssignment,
                 assignment: Assignment):
        submission.assignment = assignment
        self._submission = submission

    @property
    def id(self):
        return self._submission.id

    @property
    def score(self):
        return self._submission.grade

    @property
    def assignment_id(self):
        return self._submission.assignment_id

    @property
    def assignment(self):
        return self._submission.assignment

    @property
    def student_id(self):
        return self._submission.student_id

    def get_state(self):
        return self._submission.state_short


class GradeBookData:
    # Magic "100" constant - width of assignment column
    ASSIGNMENT_COLUMN_WIDTH = 100

    def __init__(self, course_offering, students, assignments, submissions):
        """
        X-axis of submissions ndarray is students data.
        We make some assertions on that, but still can fail in case
        of NxN array.
        """
        self.course_offering = course_offering
        assert submissions.shape == (len(students), len(assignments))
        self.students = students
        self.assignments = assignments
        self.submissions = submissions

    def get_table_width(self):
        # First 3 columns in gradebook table, see `pages/_gradebook.scss`
        magic = 150 + 140 + 66
        return len(self.assignments) * self.ASSIGNMENT_COLUMN_WIDTH + magic

    # TODO: add link to assignment and reuse in template
    def get_headers(self):
        static_headers = [
            _("Last name"),
            _("First name"),
            _("Final grade"),
            _("Total")
        ]
        return static_headers + [a.title for a in self.assignments.values()]


def gradebook_data(course_offering: CourseOffering) -> GradeBookData:
    """
    Returns:
        students = OrderedDict(
            1: StudentMeta(
                "pk": 1,
                "full_name": "serg",
                "final_grade": good,
                "total_score": 23,
                "enrollment_id": 1,
            ),
            ...
        ),
        assignments = OrderedDict(
            1: {
                "pk": 1,
                "title": "HW#1",
                "is_online": True,
                "grade_min": 0,
                "grade_max": 10
            },
            ...
        ),
        submissions = [
            [
                    {
                        "id" : 1,  # student_assignment_id
                        "score": 5
                    },
                    {
                        "id" : 3,
                        "score": 2
                    },
                    None  # if student left the course or was expelled
                          # and has no record for grading
            ],
            [ ... ]
        ]
    """
    enrolled_students = OrderedDict()
    _enrollments_qs = (Enrollment.active
                       .filter(course_offering=course_offering)
                       .select_related("student")
                       .order_by("student__last_name", "student_id"))
    for index, e in enumerate(_enrollments_qs.iterator()):
        enrolled_students[e.student_id] = StudentMeta(e, index)

    assignments = OrderedDict()
    assignments_id_to_index = {}
    _assignments_qs = (Assignment.objects
                       .filter(course_offering_id=course_offering.pk)
                       .only("pk",
                             "title",
                             # Assignment constructor caches course id
                             "course_offering_id",
                             "is_online",
                             "grade_max",
                             "grade_min")
                       .order_by("deadline_at", "pk"))
    for index, a in enumerate(_assignments_qs.iterator()):
        assignments[a.pk] = a
        assignments_id_to_index[a.pk] = index
    submissions = np.empty((len(enrolled_students), len(assignments)),
                           dtype=object)
    _student_assignments_qs = (
        StudentAssignment.objects
        .filter(assignment__course_offering_id=course_offering.pk)
        .only("pk",
              "grade",
              "first_submission_at",  # needs to calculate progress status
              "assignment_id",
              "student_id")
        .order_by("student_id", "assignment_id"))
    for sa in _student_assignments_qs.iterator():
        student_id = sa.student_id
        if student_id not in enrolled_students:
            continue
        student_index = enrolled_students[student_id].index
        assignment_index = assignments_id_to_index[sa.assignment_id]
        submissions[student_index][assignment_index] = SubmissionData(
            sa, assignments[sa.assignment_id])
    for student_id in enrolled_students:
        student_index = enrolled_students[student_id].index
        total_score = sum(s.score for s in submissions[student_index]
                          if s is not None and s.score is not None)
        setattr(enrolled_students[student_id], "total_score", total_score)

    return GradeBookData(course_offering=course_offering,
                         students=enrolled_students,
                         assignments=assignments,
                         submissions=submissions)


ConflictError = namedtuple('ConflictError', ['field_name', 'unsaved_value'])


class BaseGradebookForm(forms.Form):
    GRADE_PREFIX = "sa_"
    FINAL_GRADE_PREFIX = "final_grade_"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conflicts = False

    def get_final_widget(self, enrollment_id):
        return self[self.FINAL_GRADE_PREFIX + str(enrollment_id)]

    def get_assignment_widget(self, student_assignment_id):
        bound_field = self[self.GRADE_PREFIX + str(student_assignment_id)]
        if bound_field.errors:
            bound_field.field.widget.attrs["class"] += " __unsaved"
        return bound_field

    def _get_initial_value(self, field_name):
        initial_prefixed_name = self.add_initial_prefix(field_name)
        field = self.fields[field_name]
        hidden_widget = field.hidden_widget()
        try:
            initial_value = field.to_python(
                hidden_widget.value_from_datadict(
                    self.data, self.files, initial_prefixed_name))
        except ValidationError:
            # Always assume data has changed if validation fails.
            initial_value = None
        return initial_value

    def save(self) -> List[ConflictError]:
        final_grade_updated = False
        errors = []
        for field_name in self.changed_data:
            if field_name.startswith(self.GRADE_PREFIX):
                current_value = self._get_initial_value(field_name)
                new_value = self.cleaned_data[field_name]
                field = self.fields[field_name]
                # This is not a conflict situation when new value already in db
                updated = (StudentAssignment.objects
                           .filter(pk=field.student_assignment_id)
                           .filter(Q(grade=current_value) | Q(grade=new_value))
                           .update(grade=new_value))
                if not updated:
                    ce = ConflictError(field_name=field_name,
                                       unsaved_value=new_value)
                    errors.append(ce)
            elif field_name.startswith(self.FINAL_GRADE_PREFIX):
                current_value = self._get_initial_value(field_name)
                new_value = self.cleaned_data[field_name]
                field = self.fields[field_name]
                updated = (Enrollment.objects
                           .filter(pk=field.enrollment_id)
                           .filter(Q(grade=current_value) | Q(grade=new_value))
                           .update(grade=new_value))
                if not updated:
                    ce = ConflictError(field_name=field_name,
                                       unsaved_value=new_value)
                    errors.append(ce)
                else:
                    final_grade_updated = True
        if final_grade_updated:
            self._course_offering.recalculate_grading_type()
        self._conflicts = bool(errors)
        return errors

    def conflicts_on_last_save(self):
        return self._conflicts


class CustomBoundField(BoundField):
    """
    Shows value provided to field constructor on rendering hidden widget.
    """
    def as_hidden(self, attrs=None, **kwargs):
        """
        Returns a string of HTML for representing this as an <input type="hidden">.
        """
        widget = self.field.hidden_widget()
        return force_text(widget.render(self.html_initial_name,
                                        self.field.hidden_initial_value,
                                        attrs=attrs))


class AssignmentScore(GradeField):
    def __init__(self, assignment, submission):
        score = submission.score
        widget = forms.TextInput(attrs={
            'class': 'cell __assignment __input',
            'max': assignment.grade_max,
            'initial': score if score is not None else ""
        })
        super().__init__(min_value=0,
                         max_value=assignment.grade_max,
                         required=False,
                         show_hidden_initial=True,
                         widget=widget)
        # Used to simplify `form.save()` method
        self.student_assignment_id = submission.id
        self.submission_score = score
        self.hidden_initial_value = self.submission_score

    def get_bound_field(self, form, field_name):
        """
        Uses custom BoundField instance that will be used when accessing the
        form field in a template.
        """
        return CustomBoundField(form, self, field_name)


class EnrollmentFinalGrade(forms.ChoiceField):
    def __init__(self, student):
        widget = forms.Select(attrs={
            'initial': student.final_grade
        })
        super().__init__(GRADES,
                         required=False,
                         show_hidden_initial=True,
                         widget=widget)
        # Used to simplify `form.save()` method
        self.enrollment_id = student.enrollment_id
        self.final_grade = student.final_grade
        self.hidden_initial_value = self.final_grade

    def get_bound_field(self, form, field_name):
        """
        Uses custom BoundField instance that will be used when accessing the
        form field in a template.
        """
        return CustomBoundField(form, self, field_name)


class GradeBookFormFactory:
    @classmethod
    def build_form_class(cls, gradebook: GradeBookData):
        """
        Creates new form.Form subclass with students scores for
        each offline assignment (which student can't pass on this site) and
        students final grades for provided course.
        Internally each field of the form uses `show_hidden_initial` feature,
        but stores value provided to field constructor
        (see `CustomBoundField`) instead of value provided to the form.
        """
        cls_dict = fields = {}
        for student_submissions in gradebook.submissions:
            for submission in student_submissions:
                # Student have no submissions after withdrawal
                if not submission:
                    continue
                assignment = submission.assignment
                if not assignment.is_online:
                    k = BaseGradebookForm.GRADE_PREFIX + str(submission.id)
                    fields[k] = AssignmentScore(assignment, submission)

        for s in gradebook.students.values():
            k = BaseGradebookForm.FINAL_GRADE_PREFIX + str(s.enrollment_id)
            fields[k] = EnrollmentFinalGrade(s)
        cls_dict["_course_offering"] = gradebook.course_offering
        return type("GradebookForm", (BaseGradebookForm,), cls_dict)

    @classmethod
    def transform_to_initial(cls, gradebook: GradeBookData):
        initial = {}
        for student_submissions in gradebook.submissions:
            for submission in student_submissions:
                # Student have no submissions after withdrawal
                if not submission:
                    continue
                assignment = submission.assignment
                if not assignment.is_online:
                    k = BaseGradebookForm.GRADE_PREFIX + str(submission.id)
                    initial[k] = submission.score
        for s in gradebook.students.values():
            k = BaseGradebookForm.FINAL_GRADE_PREFIX + str(s.enrollment_id)
            initial[k] = s.final_grade
        return initial


def _get_user_id(request, **filters):
    ids = (CSCUser.objects
           .filter(groups__in=[CSCUser.group.STUDENT_CENTER,
                               CSCUser.group.VOLUNTEER],
                   **filters)
           .values_list('id', flat=True)
           .order_by())
    if len(ids) == 0:
        msg = _("User {} not found").format(filters)
        logger.debug(msg)
    elif len(ids) > 1:
        msg = _("Multiple objects found for {}").format(filters)
        logger.error(msg)
        messages.error(request, msg)
    else:
        return ids[0]


class AssignmentGradesImport:
    headers = None

    def __init__(self, request, assignment):
        self.assignment = assignment
        self.request = request
        file = request.FILES['csv_file']
        self.reader = unicodecsv.DictReader(iter(file))
        self.total = 0
        self.success = 0
        self.errors = []
        if not self.headers:
            raise ImproperlyConfigured(
                "subclasses of ImportGrade must provide headers attribute")

    def import_data(self):
        if not self.headers_are_valid():
            messages.error(self.request, "<br>".join(self.errors))
            return self.import_results()

        for row in self.reader:
            self.total += 1
            try:
                data = self.clean_data(row)
                res = self.update_score(data)
                self.success += int(res)
            except ValidationError as e:
                logger.debug(e.message)
        return self.import_results()

    def headers_are_valid(self):
        headers = self.reader.fieldnames
        valid = True
        for header in self.headers:
            if header not in headers:
                valid = False
                self.errors.append(
                    "ERROR: header `{}` not found".format(header))
        return valid

    def import_results(self):
        messages.info(self.request,
                      _("<b>Import results</b>: {}/{} successes").format(
                          self.success, self.total))
        return {'success': self.success, 'total': self.total,
                'errors': self.errors}

    def clean_data(self, row):
        raise NotImplementedError(
            'subclasses of ImportGrade must provide clean_data() method')

    def update_score(self, data):
        raise NotImplementedError(
            'subclasses of ImportGrade must provide update_score() method')


class AssignmentGradesImport:
    def __init__(self, assignment, csv_file, lookup_field, request=None):
        self.assignment = assignment
        self.reader = unicodecsv.DictReader(iter(csv_file))
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
              .filter(course_offering_id=self.assignment.course_offering_id)
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
                logger.error(e.message)
        return total, success

    def clean(self, row):
        lookup_field_value = row[self.lookup_field].strip()
        try:
            grade_field = AssignmentGradeForm.declared_fields['grade']
            score = grade_field.to_python(row["total"])
        except ValidationError:
            msg = _("Can't convert points for user '{}'").format(
                lookup_field_value)
            raise ValidationError(msg, code='invalid_score_value')
        if score > self.assignment.grade_max:
            msg = _("Score is greater than max grade for user '{}'").format(
                lookup_field_value)
            raise ValidationError(msg, code='invalid_score_value')
        return lookup_field_value, score

    def update_score(self, student_id, score):
        assignment_id = self.assignment.pk
        updated = (StudentAssignment.objects
                   .filter(assignment__id=assignment_id,
                           student_id=student_id)
                   .update(grade=score))
        if not updated:
            return False
        logger.debug(f"{score} points has written to student {student_id}")
        return True
