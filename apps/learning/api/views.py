from django.utils.translation import ugettext_lazy as _
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from api.pagination import StandardPagination
from api.permissions import CuratorAccessPermission
from learning.api.serializers import AlumniSerializer, \
    TestimonialCardSerializer, \
    CourseNewsNotificationSerializer
from learning.models import CourseNewsNotification, GraduateProfile
from study_programs.models import AcademicDiscipline


class AlumniList(ListAPIView):
    """Retrieves data for alumni/ page"""
    pagination_class = None
    serializer_class = AlumniSerializer

    def get_queryset(self):
        return (GraduateProfile.active
                .prefetch_related("academic_disciplines")
                .order_by("-graduation_year",
                          "student__last_name",
                          "student__first_name"))

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        areas = {a.code: a.name for a in AcademicDiscipline.objects.all()}
        serializer = self.get_serializer(queryset, many=True)
        data = {
            "data": serializer.data,
            "cities": {
                "spb": _("Saint Petersburg"),
                "nsk": _("Novosibirsk")
            },
            "areas": areas,
        }
        return Response(data)


class TestimonialList(ListAPIView):
    # FIXME: Add index for pagination if limit/offset is too slow
    pagination_class = StandardPagination
    serializer_class = TestimonialCardSerializer

    def get_queryset(self):
        return (GraduateProfile.active
                .with_testimonial()
                .prefetch_related("academic_disciplines")
                .order_by("-graduation_year", "pk"))

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
