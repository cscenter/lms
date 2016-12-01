from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.permissions import CuratorAccessPermission
from learning.models import CourseOffering, Enrollment
from stats.serializers import ParticipantsStatsSerializer
from users.models import CSCUser


class CourseParticipantsStatsByGroup(APIView):
    """
    Aggregate stats about course offering participants.
    """
    http_method_names = ['get']
    permission_classes = [CuratorAccessPermission]

    def get(self, request, course_session_id, format=None):
        participants = (CSCUser.objects
                        .only("curriculum_year")
                        .filter(enrollment__course_offering_id=course_session_id)
                        .prefetch_related("groups")
                        .order_by())

        serializer = ParticipantsStatsSerializer(participants, many=True)
        return Response(serializer.data)
