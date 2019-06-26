from rest_framework.generics import ListAPIView

from publications.api.serializers import OpenLectureVideoSerializer
from publications.models import OpenLecture


class OpenLectureVideoList(ListAPIView):
    pagination_class = None
    serializer_class = OpenLectureVideoSerializer

    def get_queryset(self):
        return (OpenLecture.objects
                .prefetch_related("speakers")
                .order_by('-date_at'))
