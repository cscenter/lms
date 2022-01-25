from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_pandas import PandasView

from django.db.models import Case, CharField, F, Prefetch, Value, When

from api.permissions import CuratorAccessPermission
from api.utils import get_serializer_fields, inline_serializer
from courses.models import Assignment
from learning.api.serializers import StudentProfileSerializer, UserSerializer
from learning.models import Enrollment, StudentAssignment
from learning.settings import StudentStatuses
from stats.renderers import ListRenderersMixin
from users.models import StudentProfile

from .pandas_serializers import (
    StudentsTotalByTypePandasSerializer, StudentsTotalByYearPandasSerializer
)
from .serializers import StudentAssignmentStatsSerializer


class CourseParticipantsStatsByType(ListRenderersMixin, PandasView):
    """
    Aggregate stats how many students of each type participate in the course
    """
    permission_classes = [CuratorAccessPermission]

    class OutputSerializer(serializers.ModelSerializer):
        type = serializers.CharField(source="student_type")

        class Meta:
            list_serializer_class = StudentsTotalByTypePandasSerializer
            model = StudentProfile
            fields = ("year_of_admission", "type")

    def get_serializer(self, *args, **kwargs):
        return self.OutputSerializer(*args, **kwargs)

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        # `graduate` is actually a status, not a real profile type.
        # Also its value inconsistent since it changes after student graduation
        student_type_annotation = Case(When(status=StudentStatuses.GRADUATE, then=Value('graduate')),
                                       default=F('type'),
                                       output_field=CharField())
        return (StudentProfile.objects
                .filter(enrollment__is_deleted=False,
                        enrollment__course_id=course_id)
                .only('year_of_admission', 'type')
                .annotate(student_type=student_type_annotation))


class CourseParticipantsStatsByYear(ListRenderersMixin, PandasView):
    """
    Groups students of the course by year of admission and
    counts how many of them are in each group.
    """
    permission_classes = [CuratorAccessPermission]

    class OutputSerializer(serializers.ModelSerializer):
        class Meta:
            list_serializer_class = StudentsTotalByYearPandasSerializer
            model = StudentProfile
            fields = ("year_of_admission",)

    def get_serializer(self, *args, **kwargs):
        return self.OutputSerializer(*args, **kwargs)

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        return (StudentProfile.objects
                .filter(enrollment__is_deleted=False,
                        enrollment__course_id=course_id)
                .only('year_of_admission'))


class AssignmentsStats(APIView):
    """Aggregate stats about course assignments progress"""
    permission_classes = [CuratorAccessPermission]

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField(read_only=True)
        is_online = serializers.ReadOnlyField()
        title = serializers.CharField(read_only=True)
        deadline_at = serializers.DateTimeField(label="deadline", read_only=True)
        passing_score = serializers.IntegerField(read_only=True)
        maximum_score = serializers.IntegerField(read_only=True)
        students = StudentAssignmentStatsSerializer(many=True, read_only=True)

    def get(self, request, **kwargs):
        assignments = self.get_queryset()
        data = self.OutputSerializer(assignments, many=True).data
        return Response(data)

    def get_queryset(self):
        course_id = self.kwargs["course_id"]
        # On client this stats used in conjunction with EnrollmentsStats API
        # which returns active enrollments and as a result it doesn't
        # return all student profiles.
        # After student left the course we store student progress (TODO: make sure it's as written)
        #  and don't soft delete related StudentAssignment objects. It means
        #  we miss student profile data for this records on client.
        # To avoid this error let's filter out assignments of students who
        # left the course, but better option is to return all required data
        # in EnrollmentsStats (or any other API view) and don't miss this stats.
        active_students = (Enrollment.active
                           .filter(course_id=course_id)
                           .values_list("student_id", flat=True))
        return (Assignment.objects
                .filter(course_id=course_id)
                .only("pk", "title", "course_id", "deadline_at",
                      "passing_score", "maximum_score", "submission_type")
                .prefetch_related(
                    Prefetch(
                        "studentassignment_set",
                        queryset=(StudentAssignment.objects
                                  .filter(student_id__in=active_students)
                                  .select_related("assignment")
                                  .only("pk", "assignment_id", "student_id",
                                        "score",
                                        "status",
                                        "meta",
                                        "first_student_comment_at",
                                        "assignment__course_id",
                                        "assignment__maximum_score",
                                        "assignment__passing_score",
                                        "assignment__submission_type")
                                  .order_by()),
                        to_attr="students"
                    ),
                )
                .order_by("deadline_at"))


class EnrollmentsStats(APIView):
    """
    Aggregate stats about course enrollment progress.
    """
    permission_classes = [CuratorAccessPermission]

    class OutputSerializer(serializers.Serializer):
        grade = serializers.CharField(read_only=True)
        student_profile = inline_serializer(fields={
            **get_serializer_fields(StudentProfileSerializer, fields=('type', 'status', 'year_of_curriculum')),
            "user": UserSerializer(fields=('id', 'gender'))
        })

    def get(self, request, course_id):
        enrollments = (Enrollment.active
                       .select_related("student_profile__user")
                       .only("pk", "grade", "student_profile_id")
                       .filter(course_id=course_id)
                       .order_by())
        serializer = self.OutputSerializer(enrollments, many=True)
        return Response(serializer.data)
