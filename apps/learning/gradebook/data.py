from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional

import numpy as np

from django.conf import settings
from django.db.models import Q
from django.utils.functional import cached_property

from core.db.utils import normalize_score
from courses.constants import AssignmentStatuses
from courses.models import Assignment, Course
from learning.models import Enrollment, StudentAssignment, StudentGroup
from learning.settings import GradeTypes

__all__ = ('GradebookStudent', 'GradeBookData', 'gradebook_data')


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
    def final_grade_display(self):
        return GradeTypes.values[self.final_grade]

    @property
    def student(self):
        return self._enrollment.student

    @property
    def student_profile(self):
        return self._enrollment.student_profile

    @property
    def student_group(self) -> Optional[StudentGroup]:
        if self._enrollment.student_group_id:
            return self._enrollment.student_group
        return None

    @property
    def student_type(self) -> str:
        return self.student_profile.type


@dataclass
class GradebookAssignment:
    index: int
    assignment: Assignment


class GradeBookData:
    # Magic "100" constant - width of assignment column
    ASSIGNMENT_COLUMN_WIDTH = 100

    def __init__(self,
                 course: Course,
                 students: Dict[int, GradebookStudent],
                 assignments: Dict[int, GradebookAssignment],
                 student_assignments: np.ndarray,
                 show_weight: Optional[bool] = False):
        """
        X-axis of student_assignments ndarray is students data.
        We make some assertions on that, but still can fail in case
        of NxN array.
        """
        self.course = course
        assert student_assignments.shape == (len(students), len(assignments))
        self.students = students
        self.assignments = assignments
        self.student_assignments = student_assignments
        self.show_weight = show_weight

    def get_table_width(self):
        # First 3 columns in gradebook table, see `pages/_gradebook.scss`
        magic = 150 + 140 + 66
        return len(self.assignments) * self.ASSIGNMENT_COLUMN_WIDTH + magic

    @cached_property
    def number_of_fields(self):
        # Note: assignment field uses hidden input for current value
        inputs_for_assignments = len(self.assignments) * len(self.students) * 2
        fields_for_final_grades = len(self.students)
        return inputs_for_assignments + fields_for_final_grades

    @cached_property
    def is_readonly(self):
        """
        Later based on this property value decide should assignment fields
        be read only or not in the gradebook form.
        """
        max_number = settings.DATA_UPLOAD_MAX_NUMBER_FIELDS
        number_of_fields_is_exceeded = (self.number_of_fields > max_number)
        return len(self.students) > 100 or number_of_fields_is_exceeded

    def get_personal_assignment(self, student_id: int,
                                assignment_id: int) -> StudentAssignment:
        student_index = self.students[student_id].index
        assignment_index = self.assignments[assignment_id].index
        return self.student_assignments[student_index][assignment_index]


def gradebook_data(course: Course, student_group: Optional[int] = None) -> GradeBookData:
    """
    Returns:
        students = OrderedDict(
            1: GradebookStudent(
                "pk": 1,
                "full_name": "Ivan Ivanov",
                "final_grade": "good",
                "total_score": 23,
                "enrollment_id": 1,
                "type": "invited"  # StudentTypes.INVITED
            ),
            ...
        ),
        assignments = OrderedDict(
            1: GradebookAssignment(...)
            ...
        ),
        student_assignments = [
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
    course_enrollments = (Enrollment.active
                          .filter(course=course))
    if student_group is not None:
        course_enrollments = course_enrollments.filter(student_group=student_group)
    enrollments = (course_enrollments
                   .select_related("student",
                                   "student_profile__branch",
                                   "student_group")
                   .order_by("student__last_name", "pk"))
    for index, e in enumerate(enrollments.iterator()):
        enrolled_students[e.student_id] = GradebookStudent(e, index)
    # Collect course assignments
    assignments = OrderedDict()
    queryset = Assignment.objects.filter(course_id=course.pk)
    if student_group is not None:
        queryset = queryset.filter(
            Q(assignmentgroup__group=student_group) |
            Q(assignmentgroup__group__isnull=True)
        )
    queryset = (queryset
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
    student_assignments = np.empty((len(enrolled_students), len(assignments)),
                                   dtype=object)
    filters = [Q(assignment__course_id=course.pk)]
    if student_group is not None:
        filters.append(Q(assignment__assignmentgroup__group=student_group) |
                       Q(assignment__assignmentgroup__group__isnull=True))
    queryset = (StudentAssignment.objects
                .filter(*filters)
                .only("pk",
                      "score",
                      "meta",
                      "assignment_id",
                      "student_id")
                .order_by("student_id", "assignment_id"))
    for student_assignment in queryset.iterator():
        student_id = student_assignment.student_id
        if student_id not in enrolled_students:
            continue
        student_index = enrolled_students[student_id].index
        gradebook_assignment = assignments[student_assignment.assignment_id]
        student_assignment.assignment = gradebook_assignment.assignment
        student_assignments[student_index][gradebook_assignment.index] = student_assignment
    # Aggregate student total score
    for student_id in enrolled_students:
        gradebook_student = enrolled_students[student_id]
        student_progress = student_assignments[gradebook_student.index]
        total_score = Decimal(0)
        for s in student_progress:
            if s is not None and s.weighted_score is not None:
                total_score += s.weighted_score
        total_score = normalize_score(total_score)
        setattr(gradebook_student, "total_score", total_score)
    show_weight = any(ga.assignment.weight < 1 for ga in assignments.values())
    return GradeBookData(course=course,
                         students=enrolled_students,
                         assignments=assignments,
                         student_assignments=student_assignments,
                         show_weight=show_weight)


def get_student_assignment_state(student_assignment: StudentAssignment) -> str:
    if student_assignment.status == AssignmentStatuses.ON_CHECKING:
        return "…"
    return student_assignment.get_score_verbose_display()
