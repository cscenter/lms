from rest_framework.generics import ListAPIView, UpdateAPIView, \
    get_object_or_404
from rest_framework.permissions import IsAuthenticated

from api.authentication import TokenAuthentication
from api.permissions import CuratorAccessPermission
from courses.models import Course, Assignment
from courses.permissions import CreateAssignment
from learning.api.serializers import CourseNewsNotificationSerializer, \
    StudentAssignmentSerializer, MyCourseSerializer, \
    MyCourseAssignmentSerializer, EnrollmentSerializer
from learning.models import CourseNewsNotification, StudentAssignment, \
    Enrollment
from learning.permissions import EditStudentAssignment, \
    ViewEnrollments


class CourseNewsUnreadNotificationsView(ListAPIView):
    permission_classes = [CuratorAccessPermission]
    serializer_class = CourseNewsNotificationSerializer

    def get_queryset(self):
        return (CourseNewsNotification.unread
                .filter(course_offering_news_id=self.kwargs.get('news_pk'))
                .select_related("user")
                .order_by("user__last_name"))


class CourseList(ListAPIView):
    """
    Returns course list the authenticated teacher participated in.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MyCourseSerializer

    def get_queryset(self):
        return (Course.objects
                .filter(teachers=self.request.user)
                .select_related('meta_course', 'semester', 'branch'))


class EnrollmentList(ListAPIView):
    """
    Returns student list participate in the course.
    """
    permission_classes = [IsAuthenticated, ViewEnrollments]
    serializer_class = EnrollmentSerializer

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.course = get_object_or_404(Course.objects.get_queryset(),
                                        pk=kwargs['course_id'])
        self.check_object_permissions(self.request, self.course)

    def get_queryset(self):
        return (Enrollment.active
                .filter(course_id=self.kwargs['course_id']))


class CourseAssignmentList(ListAPIView):
    """
    Returns assignment list of the course.
    """
    permission_classes = [IsAuthenticated, CreateAssignment]
    serializer_class = MyCourseAssignmentSerializer

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.course = get_object_or_404(Course.objects.get_queryset(),
                                        pk=kwargs['course_id'])
        # Someone who can create assignments for the course with no doubt
        # can view them. In case of view only permission we should check
        # it on object level for each assignment by calling
        # `.has_perm(ViewAssignment, assignment)` or create more precise
        # permission for that case, e.g. `.has_perm(ViewAssignments, course)`
        self.check_object_permissions(self.request, self.course)

    def get_queryset(self):
        return (Assignment.objects
                .filter(course_id=self.kwargs['course_id'])
                .order_by('-deadline_at'))


class StudentAssignmentList(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StudentAssignmentSerializer

    def get_queryset(self):
        filters = {}
        filters['course__course_teachers__teacher_id'] = self.request.user.pk
        # FIXME: Проверять доступ к курсе?
        return (StudentAssignment.objects
                .filter(assignment__course_id=self.kwargs['course_id'],
                        assignment_id=self.kwargs['assignment_id']))


class StudentAssignmentUpdate(UpdateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [EditStudentAssignment]
    serializer_class = StudentAssignmentSerializer

    def get_queryset(self):
        return StudentAssignment.objects.select_related('assignment')
