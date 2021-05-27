from rest_framework import serializers, status
from rest_framework.exceptions import ParseError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.http import Http404

from admission.models import InterviewSlot
from admission.selectors import get_interview_invitation
from admission.services import create_interview_from_slot
from api.mixins import ApiErrorsMixin
from api.permissions import CuratorAccessPermission

from .serializers import InterviewSlotBaseSerializer


class InterviewSlots(APIView):
    """
    Returns all slots for requested interview streams
    """
    permission_classes = [CuratorAccessPermission]

    def get(self, request, *args, **kwargs):
        slots = []
        if "streams[]" in request.GET:
            try:
                streams = [int(v) for v in request.GET.getlist("streams[]")]
            except ValueError:
                raise ParseError()
            slots = (InterviewSlot.objects
                     .filter(stream_id__in=streams)
                     .select_related("stream")
                     .order_by("stream__date", "start_at"))
        serializer = InterviewSlotBaseSerializer(slots, many=True)
        return Response(serializer.data)


class AppointmentInterviewCreateApi(ApiErrorsMixin, APIView):
    permission_classes = (AllowAny,)

    class InputSerializer(serializers.Serializer):
        secret_code = serializers.UUIDField(format='hex_verbose')
        year = serializers.IntegerField()
        slot_id = serializers.IntegerField()

    def post(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=kwargs)
        serializer.is_valid(raise_exception=True)
        invitation = get_interview_invitation(
            year=serializer.validated_data['year'],
            secret_code=serializer.validated_data['secret_code'])
        if not invitation:
            raise Http404

        create_interview_from_slot(invitation,
                                   slot_id=serializer.validated_data['slot_id'])

        return Response(status=status.HTTP_201_CREATED)

    def get_exception_handler(self):
        from api.views import exception_handler
        return exception_handler
