from django.conf import settings
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from api.pagination import StandardPagination
from learning.api.serializers import AlumniSerializer, TestimonialSerializer
from study_programs.models import AreaOfStudy
from users.models import User


class AlumniList(ListAPIView):
    """Retrieves data for alumni/ page"""
    pagination_class = None
    serializer_class = AlumniSerializer

    def get_queryset(self):
        return (User.objects
                .filter(groups__pk=User.roles.GRADUATE_CENTER)
                .prefetch_related("areas_of_study")
                .only("pk", "first_name", "last_name", "graduation_year",
                      "cropbox_data", "photo", "city_id", "gender")
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


class TestimonialList(ListAPIView):
    """Retrieves data for alumni page"""
    pagination_class = StandardPagination
    serializer_class = TestimonialSerializer

    def get_queryset(self):
        return (self.get_base_queryset()
                .prefetch_related("areas_of_study")
                .only("pk", "modified", "first_name", "last_name", "patronymic",
                      "graduation_year", "cropbox_data", "photo", "csc_review",
                      )
                .order_by("-graduation_year", "pk"))

    @staticmethod
    def get_base_queryset():
        return (User.objects
                .filter(groups=User.roles.GRADUATE_CENTER)
                .exclude(csc_review=''))

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        areas = {a.code: a.name for a in AreaOfStudy.objects.all()}
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Avoid paginated response from StandardPagination
        else:
            serializer = self.get_serializer(queryset, many=True)
        data = {
            "results": serializer.data,
            "areas": areas
        }
        return Response(data)
