from django.conf import settings
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from api.pagination import StandardPagination
from api.permissions import CuratorAccessPermission
from learning.api.serializers import AlumniSerializer, GraduateProfileSerializer, \
    CourseNewsNotificationSerializer
from learning.models import CourseNewsNotification, GraduateProfile
from study_programs.models import AcademicDiscipline
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
        areas = {a.code: a.name for a in AcademicDiscipline.objects.all()}
        serializer = self.get_serializer(queryset, many=True)
        data = {
            "data": serializer.data,
            "cities": settings.CITIES,
            "areas": areas,
        }
        return Response(data)


class TestimonialList(ListAPIView):
    # FIXME: Add index for pagination if limit/offset is too slow
    pagination_class = StandardPagination
    serializer_class = GraduateProfileSerializer

    def get_queryset(self):
        return (self.get_base_queryset()
                .select_related("student")
                .prefetch_related("academic_disciplines")
                .only("pk", "modified", "graduation_year", "photo",
                      "testimonial",
                      "student__photo",
                      "student__cropbox_data",
                      "student__first_name",
                      "student__last_name",
                      "student__patronymic",
                      "student__gender",)
                .order_by("-graduation_year", "pk"))

    @staticmethod
    def get_base_queryset():
        return (GraduateProfile.objects
                .filter(is_active=True)
                .exclude(testimonial=''))

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        areas = {a.code: a.name for a in AcademicDiscipline.objects.all()}
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


class CourseNewsUnreadNotificationsView(ListAPIView):
    permission_classes = [CuratorAccessPermission]
    serializer_class = CourseNewsNotificationSerializer

    def get_queryset(self):
        return (CourseNewsNotification.unread
                .filter(course_offering_news_id=self.kwargs.get('news_pk'))
                .select_related("user")
                .order_by("user__last_name"))
