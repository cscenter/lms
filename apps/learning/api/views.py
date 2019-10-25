from rest_framework.generics import ListAPIView, UpdateAPIView

from api.authentication import TokenAuthentication
from api.permissions import CuratorAccessPermission
from learning.api.serializers import CourseNewsNotificationSerializer, \
    StudentAssignmentSerializer
from learning.models import CourseNewsNotification, StudentAssignment
from learning.permissions import EditStudentAssignment


class CourseNewsUnreadNotificationsView(ListAPIView):
    permission_classes = [CuratorAccessPermission]
    serializer_class = CourseNewsNotificationSerializer

    def get_queryset(self):
        return (CourseNewsNotification.unread
                .filter(course_offering_news_id=self.kwargs.get('news_pk'))
                .select_related("user")
                .order_by("user__last_name"))


class StudentAssignmentUpdate(UpdateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [EditStudentAssignment]
    serializer_class = StudentAssignmentSerializer

    def get_queryset(self):
        return StudentAssignment.objects.select_related('assignment')
