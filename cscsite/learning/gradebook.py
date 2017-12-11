import logging
import numpy as np
import unicodecsv
from collections import OrderedDict
from math import ceil

from django import forms
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils.translation import ugettext_lazy as _

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

    def __init__(self, students, assignments, submissions):
        """
        X-axis of submissions ndarray is students data.
        We make some assertions on that, but still can fail in case
        of NxN array.
        """
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
                       .order_by("student__last_name"))
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

    return GradeBookData(students=enrolled_students,
                         assignments=assignments,
                         submissions=submissions)


class BaseGradebookForm(forms.Form):
    GRADE_PREFIX = "sa_"
    FINAL_GRADE_PREFIX = "final_grade_"

    def get_final_widget(self, enrollment_id):
        return self[self.FINAL_GRADE_PREFIX + str(enrollment_id)]

    def get_assignment_widget(self, student_assignment_id):
        return self[self.GRADE_PREFIX + str(student_assignment_id)]


class GradeBookFormFactory:
    @classmethod
    def build_form_class(cls, gradebook: GradeBookData):
        """
        Creates new form.Form subclass with StudentAssignment's and
        Enrollment's grades.
        """
        fields = {}
        for student_submissions in gradebook.submissions:
            for submission in student_submissions:
                # Student have no submissions after withdrawal
                if not submission:
                    continue
                assignment = submission.assignment
                if not assignment.is_online:
                    k = BaseGradebookForm.GRADE_PREFIX + str(submission.id)
                    v = forms.IntegerField(min_value=0,
                                           max_value=assignment.grade_max,
                                           required=False)
                    # Used to simplify `form_valid` method
                    v.student_assignment_id = submission.id
                    fields[k] = v

        for s in gradebook.students.values():
            k = BaseGradebookForm.FINAL_GRADE_PREFIX + str(s.enrollment_id)
            v = forms.ChoiceField(GRADES)
            # Used to simplify `form_valid` method
            v.enrollment_id = s.enrollment_id
            fields[k] = v
        return type("GradebookForm", (BaseGradebookForm,), fields)

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


class ImportGrades(object):
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


class ImportGradesByStepicID(ImportGrades):
    headers = ["user_id", "total"]

    def clean_data(self, row):
        stepic_id = row["user_id"].strip()
        try:
            stepic_id = int(stepic_id)
        except ValueError:
            msg = _("Can't convert user_id to int '{}'").format(stepic_id)
            raise ValidationError(msg, code='invalid_user_id')
        try:
            score = int(ceil(float(row["total"])))
        except ValueError:
            msg = _("Can't convert points for user '{}'").format(stepic_id)
            raise ValidationError(msg, code='invalid_score_value')
        if score > self.assignment.grade_max:
            msg = _("Score greater than max value for id '{}'").format(stepic_id)
            raise ValidationError(msg, code='invalid_score_value')
        return stepic_id, score

    def update_score(self, data):
        stepic_id, score = data
        assignment_id = self.assignment.pk

        user_id = _get_user_id(self.request, stepic_id=stepic_id)
        if not user_id:
            return False

        updated = (StudentAssignment.objects
                   .filter(assignment__id=assignment_id,
                           student_id=user_id)
                   .update(grade=score))
        if not updated:
            msg = "User with id={} and stepic_id={} doesn't have " \
                  "an assignment {}".format(user_id, stepic_id, assignment_id)
            logger.debug(msg)
            return False
        logger.debug("Has written {} points for user_id={} on assignment_id={}"
                     .format(score, user_id, assignment_id))
        return True


class ImportGradesByYandexLogin(ImportGrades):
    headers = ["login", "total"]

    def clean_data(self, row):
        yandex_id = row['login'].strip()
        try:
            score = int(ceil(float(row["total"])))
        except ValueError:
            msg = _("Can't convert points for user '{}'").format(yandex_id)
            raise ValidationError(msg, code='invalid_score_value')
        if score > self.assignment.grade_max:
            msg = _("Score greater then max grade for user '{}'").format(yandex_id)
            raise ValidationError(msg, code='invalid_score_value')
        return yandex_id, score

    def update_score(self, data):
        yandex_id, score = data
        from learning.models import StudentAssignment

        assignment_id = self.assignment.pk

        user_id = _get_user_id(self.request, yandex_id__iexact=yandex_id)
        if not user_id:
            return False

        updated = (StudentAssignment.objects
                   .filter(assignment__id=assignment_id,
                           student_id=user_id)
                   .update(grade=score))
        if not updated:
            msg = "User with id={} and yandex_id={} doesn't have " \
                  "an assignment".format(user_id, yandex_id)
            logger.debug(msg)
            return False
        logger.debug("Has written {} points for user_id={} on assignment_id={}"
                     .format(score, user_id, assignment_id))
        return True

