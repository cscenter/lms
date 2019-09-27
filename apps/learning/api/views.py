from rest_framework.generics import ListAPIView

from api.permissions import CuratorAccessPermission
from learning.api.serializers import CourseNewsNotificationSerializer
from learning.models import CourseNewsNotification


class CourseNewsUnreadNotificationsView(ListAPIView):
    permission_classes = [CuratorAccessPermission]
    serializer_class = CourseNewsNotificationSerializer

    def get_queryset(self):
        return (CourseNewsNotification.unread
                .filter(course_offering_news_id=self.kwargs.get('news_pk'))
                .select_related("user")
                .order_by("user__last_name"))
