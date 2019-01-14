import logging

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from vanilla import TemplateView

from api.permissions import CuratorAccessPermission
from learning.models import CourseNewsNotification
from courses.models import Course
from learning.api.serializers import CourseNewsNotificationSerializer
from users.mixins import TeacherOnlyMixin

__all__ = ['CourseNewsUnreadNotificationsView',
           'CourseStudentsView']


logger = logging.getLogger(__name__)


class CourseStudentsView(TeacherOnlyMixin, TemplateView):
    # raise_exception = True
    template_name = "learning/courseoffering_students.html"

    def get(self, request, *args, **kwargs):
        try:
            year, _ = self.kwargs['semester_slug'].split("-", 1)
            _ = int(year)
        except ValueError:
            raise Http404
        return super().get(request, *args, **kwargs)

    def handle_no_permission(self, request):
        raise Http404

    def get_context_data(self, **kwargs):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        co = get_object_or_404(Course.objects
                               .filter(semester__type=semester_type,
                                       semester__year=year,
                                       meta_course__slug=self.kwargs['course_slug'])
                               .in_city(self.request.city_code))
        return {
            "co": co,
            "enrollments": (co.enrollment_set(manager="active")
                            .select_related("student"))
        }


class CourseNewsUnreadNotificationsView(ListAPIView):
    permission_classes = [CuratorAccessPermission]
    serializer_class = CourseNewsNotificationSerializer

    def get_queryset(self):
        return (CourseNewsNotification.unread
                .filter(course_offering_news_id=self.kwargs.get('news_pk'))
                .select_related("user")
                .order_by("user__last_name"))
