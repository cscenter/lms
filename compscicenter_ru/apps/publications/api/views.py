from rest_framework.generics import ListAPIView

from publications.api.serializers import RecordedEventSerializer
from publications.models import RecordedEvent


class RecordedEventList(ListAPIView):
    pagination_class = None
    serializer_class = RecordedEventSerializer

    def get_queryset(self):
        return (RecordedEvent.objects
                .prefetch_related("speakers")
                .order_by('-date_at'))
