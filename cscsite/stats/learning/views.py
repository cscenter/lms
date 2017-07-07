from django.contrib.auth.models import Group
from django.db.models import Prefetch
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_pandas import PandasView

from api.permissions import CuratorAccessPermission
from learning.models import StudentAssignment, \
    Assignment, Enrollment
from stats.renderers import ListRenderersMixin
from users.models import CSCUser
from .pandas_serializers import ParticipantsByYearPandasSerializer, \
    ParticipantsByGroupPandasSerializer
from .serializers import ParticipantsStatsSerializer, \
    AssignmentsStatsSerializer, EnrollmentsStatsSerializer


class CourseParticipantsStatsByGroup(ListRenderersMixin, PandasView):
    """
    Aggregate stats about course offering participants.
    """
    permission_classes = [CuratorAccessPermission]
    serializer_class = ParticipantsStatsSerializer
    pandas_serializer_class = ParticipantsByGroupPandasSerializer

    def get_queryset(self):
        STUDENT_GROUPS = [
            CSCUser.group.STUDENT_CENTER,
            CSCUser.group.VOLUNTEER,
            CSCUser.group.GRADUATE_CENTER,
        ]
        course_offering_id = self.kwargs['course_session_id']
        return (CSCUser.objects
                .only("curriculum_year")
                .filter(
                    enrollment__is_deleted=False,
                    enrollment__course_offering_id=course_offering_id)
                .prefetch_related(
                    Prefetch(
                        "groups",
                        queryset=Group.objects.filter(pk__in=STUDENT_GROUPS)
                    )
                )
                .order_by())


class CourseParticipantsStatsByYear(ListRenderersMixin, PandasView):
    """
    Aggregate stats about course offering participants.
    """
    permission_classes = [CuratorAccessPermission]
    serializer_class = ParticipantsStatsSerializer
    pandas_serializer_class = ParticipantsByYearPandasSerializer

    def get_queryset(self):
        course_offering_id = self.kwargs['course_session_id']
        return (CSCUser.objects
                .only("curriculum_year")
                .filter(
                    enrollment__is_deleted=False,
                    enrollment__course_offering_id=course_offering_id)
                .prefetch_related("groups")
                .order_by())


class AssignmentsStats(APIView):
    """
    Aggregate stats about course offering assignment progress.
    """
    http_method_names = ['get']
    permission_classes = [CuratorAccessPermission]

    def get(self, request, course_session_id, format=None):
        active_students = (Enrollment.active.filter(
                course_offering_id=course_session_id)
            .values_list("student_id", flat=True))
        assignments = (Assignment
                       .objects
                       .only("pk", "title", "course_offering_id", "deadline_at",
                             "grade_min", "grade_max", "is_online")
                       .filter(course_offering_id=course_session_id)
                       .prefetch_related(
            Prefetch(
                "assigned_to",
                # FIXME: что считать всё-таки сданным. Там где есть оценка?
                queryset=(StudentAssignment.objects
                          .filter(student_id__in=active_students)
                          .select_related("student", "assignment")
                          .prefetch_related("student__groups")
                          .only("pk", "assignment_id", "grade",
                                "student_id", "first_submission_at",
                                "student__gender", "student__curriculum_year",
                                "assignment__course_offering_id",
                                "assignment__grade_max",
                                "assignment__grade_min",
                                "assignment__is_online")
                          .order_by())
            ))
                       .order_by("deadline_at"))
        serializer = AssignmentsStatsSerializer(assignments, many=True)
        return Response(serializer.data)


class EnrollmentsStats(APIView):
    """
    Aggregate stats about course offering assignment progress.
    """
    http_method_names = ['get']
    permission_classes = [CuratorAccessPermission]

    def get(self, request, course_session_id, format=None):
        enrollments = (Enrollment.active
                       .only("pk", "grade", "student_id", "student__gender",
                             "student__curriculum_year")
                       .select_related("student")
                       .filter(course_offering_id=course_session_id)
                       .order_by())

        serializer = EnrollmentsStatsSerializer(enrollments, many=True)
        return Response(serializer.data)
