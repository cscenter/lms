from collections import OrderedDict
import numpy as np

from django import forms

from learning.models import StudentAssignment, Enrollment, Assignment
from learning.settings import GRADES
from users.models import CSCUser


class StudentMeta:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_abbreviated_name(self):
        # noinspection PyCallByClass
        return CSCUser.get_abbreviated_name(self)

    @property
    def final_grade_display(self):
        return GRADES[self.final_grade]


class GradeBookData:
    """
    Note:
        X-axis of submissions ndarray is students data.
        We make some assertions on that, but fail in case of NxN array.
    """
    def __init__(self, students, assignments, submissions):
        self.students = students
        self.assignments = assignments
        assert submissions.shape == (len(students), len(assignments))
        self.submissions = submissions


def gradebook_data(course_offering):
    """
    Returns:
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
    students_id_to_index = {}
    _enrollments_qs = (Enrollment.active
                       .filter(course_offering=course_offering)
                       .select_related("student")
                       .order_by("student__last_name"))
    for index, e in enumerate(_enrollments_qs.iterator()):
        enrolled_students[e.student_id] = StudentMeta(
            pk=e.student_id,
            enrollment_id=e.pk,
            final_grade=e.grade,
            first_name=e.student.first_name,
            last_name=e.student.last_name,
            patronymic=e.student.patronymic,
            username=e.student.username,
            yandex_id=e.student.yandex_id,
            total_score=None,  # Will be filled later based on assignments data
        )
        students_id_to_index[e.student_id] = index

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
              "assignment_id",
              "student_id")
        .order_by("student_id", "assignment_id"))
    for sa in _student_assignments_qs.iterator():
        student_id = sa.student_id
        if student_id not in enrolled_students:
            continue
        student_index = students_id_to_index[student_id]
        assignment_index = assignments_id_to_index[sa.assignment_id]
        submissions[student_index][assignment_index] = {
            "id": sa.pk,
            "score": sa.grade,
            # Append ids to simplify access in the future
            "assignment_id": sa.assignment_id,
            "student_id": student_id,
        }
    for student_id in enrolled_students:
        student_index = students_id_to_index[student_id]
        total_score = sum(a["score"] for a in submissions[student_index]
                          if a is not None and a.get("score") is not None)
        setattr(enrolled_students[student_id], "total_score", total_score)

    return GradeBookData(assignments=assignments,
                         students=enrolled_students,
                         submissions=submissions)


class GradeBookFormFactory:

    GRADE_PREFIX = "sa_{0}"
    FINAL_GRADE_PREFIX = "final_grade_{0}"

    @classmethod
    def build_form_class(cls, gradebook: GradeBookData):
        """
        Creates new form.Form subclass with StudentAssignment's and
        Enrollment's grades.
        """
        fields = {}

        for student_submissions in gradebook.submissions:
            for submission in student_submissions:
                assignment = gradebook.assignments[submission["assignment_id"]]
                if not assignment.is_online:
                    k = cls.GRADE_PREFIX.format(submission["id"])
                    v = forms.IntegerField(min_value=assignment.grade_min,
                                           max_value=assignment.grade_max,
                                           required=False)
                    fields[k] = v

        for student in gradebook.students.values():
            k = cls.FINAL_GRADE_PREFIX.format(student.enrollment_id)
            fields[k] = forms.ChoiceField(GRADES)
        return type('GradebookForm', (forms.Form,), fields)

    @classmethod
    def build_indexes(cls, student_assignments_list, enrollment_list):
        sas = student_assignments_list
        a_s_index = {cls.GRADE_PREFIX.format(a_s["pk"]): a_s for a_s in sas}
        enrollment_index = {cls.FINAL_GRADE_PREFIX.format(e.pk): e for e in
                            enrollment_list}
        return a_s_index, enrollment_index

    @classmethod
    def transform_to_initial(cls, a_s_list, enrollment_list):
        initial = {cls.GRADE_PREFIX.format(a_s["pk"]): a_s["grade"] for a_s in
                   a_s_list if not a_s["assignment__is_online"]}
        initial.update({cls.FINAL_GRADE_PREFIX.format(e.pk): e.grade for e in
                        enrollment_list})
        return initial
