from django.conf import settings
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from learning.api.serializers import AlumniSerializer
from learning.models import AreaOfStudy
from users.models import CSCUser


class AlumniList(ListAPIView):
    """Retrieves data for alumni page"""
    pagination_class = None
    serializer_class = AlumniSerializer

    def get_queryset(self):
        return (CSCUser.objects
                .filter(groups__pk=CSCUser.group.GRADUATE_CENTER)
                .prefetch_related("areas_of_study")
                .only("pk", "first_name", "last_name", "graduation_year",
                      "cropbox_data", "city_id")
                .order_by("-graduation_year", "last_name", "first_name"))

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        areas = {a.code: a.name for a in AreaOfStudy.objects.all()}
        serializer = self.get_serializer(queryset, many=True)
        data = {
            "data": serializer.data,
            "cities": settings.CITIES,
            "areas": areas,
        }
        return Response(data)
