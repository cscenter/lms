from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict

import numpy as np
from django.utils.translation import gettext_lazy as _

from core.db.models import normalize_score
from courses.models import Course, Assignment
from learning.models import StudentAssignment, Enrollment
from learning.settings import GradeTypes


__all__ = ('GradebookStudent', 'StudentProgress', 'GradeBookData',
           'gradebook_data')


class GradebookStudent:
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

    @property
    def codeforces_login(self):
        return self._enrollment.student.codeforces_login

    def get_absolute_url(self):
        return self._enrollment.student.get_absolute_url()

    def get_abbreviated_name(self):
        return self._enrollment.student.get_abbreviated_name()

    def get_abbreviated_short_name(self):
        return self._enrollment.student.get_abbreviated_short_name()

    @property
    def final_grade_display(self):
        return GradeTypes.values[self.final_grade]


@dataclass
class GradebookAssignment:
    index: int
    assignment: Assignment


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

    def __init__(self,
                 course: Course,
                 students: Dict[int, GradebookStudent],
                 assignments: Dict[int, GradebookAssignment],
                 submissions,
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
            1: GradebookStudent(
                "pk": 1,
                "full_name": "Ivan Ivanov",
                "final_grade": "good",
                "total_score": 23,
                "enrollment_id": 1,
            ),
            ...
        ),
        assignments = OrderedDict(
            1: GradebookAssignment(...)
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
    # Collect active enrollments
    enrolled_students = OrderedDict()
    enrollments = (Enrollment.active
                   .filter(course=course)
                   .select_related("student", "student_profile")
                   .order_by("student__last_name", "pk"))
    for index, e in enumerate(enrollments.iterator()):
        enrolled_students[e.student_id] = GradebookStudent(e, index)
    # Collect course assignments
    assignments = OrderedDict()
    queryset = (Assignment.objects
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
    for index, a in enumerate(queryset.iterator()):
        assignments[a.pk] = GradebookAssignment(index, assignment=a)
    # Collect students progress
    submissions = np.empty((len(enrolled_students), len(assignments)),
                           dtype=object)
    queryset = (StudentAssignment.objects
                .filter(assignment__course_id=course.pk)
                .only("pk",
                      "score",
                      # needs to calculate progress status
                      "first_student_comment_at",
                      "assignment_id",
                      "student_id")
                .order_by("student_id", "assignment_id"))
    for student_assignment in queryset.iterator():
        student_id = student_assignment.student_id
        if student_id not in enrolled_students:
            continue
        student_index = enrolled_students[student_id].index
        gradebook_assignment = assignments[student_assignment.assignment_id]
        submissions[student_index][gradebook_assignment.index] = StudentProgress(
            student_assignment, gradebook_assignment.assignment)
    # Aggregate student total score
    for student_id in enrolled_students:
        gradebook_student = enrolled_students[student_id]
        student_submissions = submissions[gradebook_student.index]
        total_score = Decimal(0)
        for s in student_submissions:
            if s is not None and s.weight_score is not None:
                total_score += s.weight_score
        total_score = normalize_score(total_score)
        setattr(gradebook_student, "total_score", total_score)
    show_weight = any(ga.assignment.weight < 1 for ga in assignments.values())
    return GradeBookData(course=course,
                         students=enrolled_students,
                         assignments=assignments,
                         submissions=submissions,
                         show_weight=show_weight)
