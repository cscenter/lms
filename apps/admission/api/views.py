from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from rest_framework.views import APIView

from admission.models import InterviewSlot
from api.permissions import CuratorAccessPermission
from .serializers import InterviewSlotSerializer


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
        serializer = InterviewSlotSerializer(slots, many=True)
        return Response(serializer.data)
