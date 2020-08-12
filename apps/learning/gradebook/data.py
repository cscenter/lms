from collections import OrderedDict
from decimal import Decimal

import numpy as np
from django.utils.translation import gettext_lazy as _

from core.db.models import normalize_score
from courses.models import Course, Assignment
from learning.models import StudentAssignment, Enrollment
from learning.settings import GradeTypes


__all__ = ('StudentMeta', 'StudentProgress', 'GradeBookData', 'gradebook_data')


class StudentMeta:
    def __init__(self, enrollment: Enrollment, index: int):
        self._enrollment = enrollment
        self.index = index  # Row index in enrolled students list
        # Will be filled later based on assignments data
        self.total_score = None
        self.achieved = None  # expressed in percentages

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
    def email(self):
        return self._enrollment.student.email

    @property
    def yandex_login(self):
        return self._enrollment.student.yandex_login

    def get_absolute_url(self):
        return self._enrollment.student.get_absolute_url()

    def get_abbreviated_name(self):
        return self._enrollment.student.get_abbreviated_name()

    def get_abbreviated_short_name(self):
        return self._enrollment.student.get_abbreviated_short_name()

    @property
    def final_grade_display(self):
        return GradeTypes.values[self.final_grade]


class StudentProgress:
    def __init__(self, student_assignment: StudentAssignment,
                 assignment: Assignment):
        student_assignment.assignment = assignment
        self._student_assignment = student_assignment

    @property
    def id(self):
        return self._student_assignment.id

    @property
    def score(self):
        return self._student_assignment.score

    @property
    def weight_score(self):
        return self._student_assignment.weight_score

    @property
    def assignment_id(self):
        return self._student_assignment.assignment_id

    @property
    def assignment(self):
        return self._student_assignment.assignment

    def get_teacher_url(self):
        return self._student_assignment.get_teacher_url()

    @property
    def student_id(self):
        return self._student_assignment.student_id

    def get_state(self):
        return self._student_assignment.state_short


class GradeBookData:
    # Magic "100" constant - width of assignment column
    ASSIGNMENT_COLUMN_WIDTH = 100

    def __init__(self, course: Course, students, assignments, submissions,
                 show_weight=False):
        """
        X-axis of submissions ndarray is students data.
        We make some assertions on that, but still can fail in case
        of NxN array.
        """
        self.course = course
        assert submissions.shape == (len(students), len(assignments))
        self.students = students
        self.assignments = assignments
        self.submissions = submissions
        self.show_weight = show_weight

    def get_table_width(self):
        # First 3 columns in gradebook table, see `pages/_gradebook.scss`
        magic = 150 + 140 + 66
        return len(self.assignments) * self.ASSIGNMENT_COLUMN_WIDTH + magic


def gradebook_data(course: Course) -> GradeBookData:
    """
    Returns:
        students = OrderedDict(
            1: StudentMeta(
                "pk": 1,
                "full_name": "Ivan Ivanov",
                "final_grade": "good",
                "total_score": 23,
                "enrollment_id": 1,
            ),
            ...
        ),
        assignments = OrderedDict(
            1: Assignment(...)
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
                       .filter(course=course)
                       .select_related("student")
                       .order_by("student__last_name", "student_id"))
    for index, e in enumerate(_enrollments_qs.iterator()):
        enrolled_students[e.student_id] = StudentMeta(e, index)

    assignments = OrderedDict()
    assignments_id_to_index = {}
    _assignments_qs = (Assignment.objects
                       .filter(course_id=course.pk)
                       .only("pk",
                             "title",
                             # Assignment constructor caches course id
                             "course_id",
                             "submission_type",
                             "maximum_score",
                             "passing_score",
                             "weight")
                       .order_by("deadline_at", "pk"))
    for index, a in enumerate(_assignments_qs.iterator()):
        assignments[a.pk] = a
        assignments_id_to_index[a.pk] = index
    submissions = np.empty((len(enrolled_students), len(assignments)),
                           dtype=object)
    _student_assignments_qs = (
        StudentAssignment.objects
        .filter(assignment__course_id=course.pk)
        .only("pk",
              "score",
              "first_student_comment_at",  # needs to calculate progress status
              "assignment_id",
              "student_id")
        .order_by("student_id", "assignment_id"))
    for sa in _student_assignments_qs.iterator():
        student_id = sa.student_id
        if student_id not in enrolled_students:
            continue
        student_index = enrolled_students[student_id].index
        assignment_index = assignments_id_to_index[sa.assignment_id]
        submissions[student_index][assignment_index] = StudentProgress(
            sa, assignments[sa.assignment_id])
    for student_id in enrolled_students:
        student_index = enrolled_students[student_id].index
        student_submissions = submissions[student_index]
        total_score = sum(s.score for s in student_submissions
                          if s is not None and s.score is not None)
        setattr(enrolled_students[student_id], "total_score", total_score)
        total_score = Decimal(0)
        for s in student_submissions:
            if s is not None and s.weight_score is not None:
                total_score += s.weight_score
        total_score = normalize_score(total_score)
        setattr(enrolled_students[student_id], "total_score", total_score)
    show_weight = any(a.weight < 1 for a in assignments.values())
    return GradeBookData(course=course,
                         students=enrolled_students,
                         assignments=assignments,
                         submissions=submissions,
                         show_weight=show_weight)
