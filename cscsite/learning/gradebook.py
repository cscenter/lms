from collections import OrderedDict

import numpy as np

from django import forms
from django.utils.translation import ugettext_lazy as _

from learning.models import StudentAssignment, Enrollment, Assignment, \
    CourseOffering
from learning.settings import GRADES


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
                    v = forms.IntegerField(min_value=assignment.grade_min,
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
