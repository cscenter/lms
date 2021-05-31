from rest_framework import serializers, status
from rest_framework.exceptions import ParseError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.http import Http404

from admission.models import InterviewSlot
from admission.selectors import (
    get_active_interview_invitation, get_interview_invitation
)
from admission.services import accept_interview_invitation, decline_interview_invitation
from api.permissions import CuratorAccessPermission
from api.views import APIBaseView

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


class AppointmentInterviewInvitationApi(APIBaseView):
    permission_classes = (AllowAny,)

    class InputSerializer(serializers.Serializer):
        year = serializers.IntegerField()
        secret_code = serializers.UUIDField()

    def put(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=kwargs)
        serializer.is_valid(raise_exception=True)
        invitation = get_active_interview_invitation(**serializer.validated_data)
        if not invitation:
            raise Http404

        decline_interview_invitation(invitation)

        return Response(status=status.HTTP_200_OK)


class AppointmentInterviewCreateApi(APIBaseView):
    permission_classes = (AllowAny,)

    class InputSerializer(serializers.Serializer):
        year = serializers.IntegerField()
        secret_code = serializers.UUIDField(format='hex_verbose')
        slot_id = serializers.IntegerField()

    def post(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=kwargs)
        serializer.is_valid(raise_exception=True)
        invitation = get_interview_invitation(year=serializer.validated_data['year'],
                                              secret_code=serializer.validated_data['secret_code'])
        if not invitation:
            raise Http404

        accept_interview_invitation(invitation,
                                    slot_id=serializer.validated_data['slot_id'])

        return Response(status=status.HTTP_201_CREATED)
