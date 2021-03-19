from django.conf import settings
from django.db.models import Prefetch
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_pandas import PandasView

from api.permissions import CuratorAccessPermission
from courses.models import Assignment
from learning.models import StudentAssignment, \
    Enrollment
from stats.renderers import ListRenderersMixin
from users.models import User, UserGroup, StudentProfile
from .pandas_serializers import ParticipantsByYearPandasSerializer, \
    StudentsByTypePandasSerializer
from .serializers import ParticipantsStatsSerializer, \
    AssignmentsStatsSerializer, EnrollmentsStatsSerializer


class CourseParticipantsStatsByType(ListRenderersMixin, PandasView):
    """
    Aggregate stats how many students of each type participate in the course
    """
    permission_classes = [CuratorAccessPermission]

    class OutputSerializer(serializers.ModelSerializer):
        class Meta:
            list_serializer_class = StudentsByTypePandasSerializer
            model = StudentProfile
            fields = ("year_of_admission", "type")

    def get_serializer(self, *args, **kwargs):
        return self.OutputSerializer(*args, **kwargs)

    def get_queryset(self):
        # TODO: add virtual `graduate` type (graduate is student profile status, not a type)
        course_id = self.kwargs['course_id']
        return (StudentProfile.objects
                .filter(enrollment__is_deleted=False,
                        enrollment__course_id=course_id)
                .only('year_of_admission', 'type'))


class CourseParticipantsStatsByYear(ListRenderersMixin, PandasView):
    """
    Aggregate stats about students enrolled in the course.
    """
    permission_classes = [CuratorAccessPermission]
    serializer_class = ParticipantsStatsSerializer
    pandas_serializer_class = ParticipantsByYearPandasSerializer

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        return (User.objects
                .only("curriculum_year")
                .filter(
                    enrollment__is_deleted=False,
                    enrollment__course_id=course_id)
                .prefetch_related(
                    Prefetch(
                        "groups",
                        queryset=(UserGroup.objects
                                  .filter(site_id=settings.SITE_ID))
                    )
                )
                .order_by())


class AssignmentsStats(ReadOnlyModelViewSet):
    """
    Aggregate stats about course assignment progress.
    """
    permission_classes = [CuratorAccessPermission]
    serializer_class = AssignmentsStatsSerializer

    def get_queryset(self):
        course_id = self.kwargs["course_id"]
        active_students = (Enrollment.active
                           .filter(course_id=course_id)
                           .values_list("student_id", flat=True))
        return (Assignment.objects
                .only("pk", "title", "course_id", "deadline_at",
                      "passing_score", "maximum_score", "submission_type")
                .filter(course_id=course_id)
                .prefetch_related(
                    Prefetch(
                        "studentassignment_set",
                        # FIXME: добавить smoke test
                        # FIXME: что считать всё-таки сданным. Там где есть оценка?
                        queryset=(StudentAssignment.objects
                                  .filter(student_id__in=active_students)
                                  .select_related("student", "assignment")
                                  .prefetch_related("student__groups")
                                  .only("pk", "assignment_id", "score",
                                        "student_id",
                                        "first_student_comment_at",
                                        "student__gender",
                                        "student__curriculum_year",
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
    http_method_names = ['get']
    permission_classes = [CuratorAccessPermission]

    def get(self, request, course_id, format=None):
        enrollments = (Enrollment.active
                       .only("pk", "grade", "student_id")
                       .select_related("student")
                       .filter(course_id=course_id)
                       .order_by())

        serializer = EnrollmentsStatsSerializer(enrollments, many=True)
        return Response(serializer.data)
