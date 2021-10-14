from typing import Any, Optional

from djangorestframework_camel_case.render import (
    CamelCaseBrowsableAPIRenderer, CamelCaseJSONRenderer
)
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView, UpdateAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.authentication import TokenAuthentication
from api.mixins import ApiErrorsMixin
from api.permissions import CuratorAccessPermission
from api.utils import inline_serializer
from api.views import APIBaseView
from auth.mixins import RolePermissionRequiredMixin
from core.api.fields import CharSeparatedField, ScoreField
from core.http import AuthenticatedAPIRequest
from courses.models import Assignment, Course
from courses.permissions import CreateAssignment
from courses.selectors import course_personal_assignments
from learning.api.serializers import (
    BaseEnrollmentSerializer, BaseStudentAssignmentSerializer,
    CourseAssignmentSerializer, CourseNewsNotificationSerializer, MyCourseSerializer,
    StudentAssignmentAssigneeSerializer, StudentProfileSerializer, UserSerializer
)
from learning.models import CourseNewsNotification, Enrollment, StudentAssignment
from learning.permissions import EditStudentAssignment, ViewEnrollments


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
    List courses the authenticated user participated in as a teacher.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = MyCourseSerializer

    def get_queryset(self):
        return (Course.objects
                .filter(teachers=self.request.user)
                .select_related('meta_course', 'semester', 'main_branch'))


class CourseAssignmentList(RolePermissionRequiredMixin, ApiErrorsMixin, ListAPIView):
    """List assignments of the course."""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [CreateAssignment]
    serializer_class = CourseAssignmentSerializer
    renderer_classes = (CamelCaseJSONRenderer, CamelCaseBrowsableAPIRenderer)
    course: Course

    def initial(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course.objects.get_queryset(), pk=kwargs['course_id'])
        super().initial(request, *args, **kwargs)

    def get_permission_object(self) -> Course:
        return self.course

    def get_queryset(self):
        return (Assignment.objects
                .filter(course_id=self.kwargs['course_id'])
                .order_by('-deadline_at'))


class CourseStudentsList(RolePermissionRequiredMixin, APIBaseView):
    """List of students enrolled in the course."""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [ViewEnrollments]
    renderer_classes = (CamelCaseJSONRenderer, CamelCaseBrowsableAPIRenderer)
    course: Course

    class OutputSerializer(BaseEnrollmentSerializer):
        student = UserSerializer(fields=('id', 'first_name', 'last_name', 'patronymic'))
        # TODO: consider to use expandable fields https://github.com/rsinger86/drf-flex-fields or
        #  https://github.com/evenicoulddoit/django-rest-framework-serializer-extensions
        # student_profile = StudentProfileSerializer(fields=('id', 'type', 'branch', 'year_of_admission'))

        class Meta(BaseEnrollmentSerializer.Meta):
            fields = ('id', 'grade', 'student_group_id', 'student', 'student_profile_id')

    def initial(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course.objects.get_queryset(),
                                        pk=kwargs['course_id'])
        super().initial(request, *args, **kwargs)

    def get_permission_object(self) -> Course:
        return self.course

    def get(self, request: AuthenticatedAPIRequest, **kwargs: Any):
        queryset = (Enrollment.active
                    .select_related('student')
                    .filter(course=self.course,
                            course__main_branch__site=request.site))
        data = self.OutputSerializer(queryset, many=True).data
        return Response(data)


class PersonalAssignmentList(RolePermissionRequiredMixin, APIBaseView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [CreateAssignment]
    renderer_classes = (CamelCaseJSONRenderer, CamelCaseBrowsableAPIRenderer)
    course: Course

    class FilterSerializer(serializers.Serializer):
        assignments = CharSeparatedField(label='test', allow_blank=True, required=False)

    class OutputSerializer(serializers.ModelSerializer):
        state = serializers.SerializerMethodField()
        score = ScoreField(coerce_to_string=True)
        student = UserSerializer(fields=('id', 'first_name', 'last_name', 'patronymic'))
        assignee = inline_serializer(fields={
            "id": serializers.IntegerField(),
            "teacher": UserSerializer(fields=('id', 'first_name', 'last_name', 'patronymic'))
        })
        activity = serializers.SerializerMethodField()

        class Meta:
            model = StudentAssignment
            fields = ('id', 'assignment_id', 'score', 'state', 'student',
                      'assignee', 'activity')

        def get_state(self, obj: StudentAssignment):
            return obj.state.value

        def get_activity(self, obj: StudentAssignment) -> Optional[str]:
            """Returns latest activity."""
            if not obj.meta or 'stats' not in obj.meta:
                return None
            return obj.meta['stats'].get('activity', None)

    def initial(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course.objects.get_queryset(), pk=kwargs['course_id'])
        super().initial(request, *args, **kwargs)

    def get_permission_object(self) -> Course:
        return self.course

    def get(self, request: AuthenticatedAPIRequest, **kwargs: Any):
        filters_serializer = self.FilterSerializer(data=request.query_params)
        filters_serializer.is_valid(raise_exception=True)
        personal_assignments = course_personal_assignments(course=self.course,
                                                           filters=filters_serializer.validated_data)
        data = self.OutputSerializer(personal_assignments, many=True).data
        return Response(data)


class StudentAssignmentUpdate(UpdateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [EditStudentAssignment]
    serializer_class = BaseStudentAssignmentSerializer
    lookup_url_kwarg = 'student_id'
    lookup_field = 'student_id'

    def get_queryset(self):
        return (StudentAssignment.objects
                .filter(assignment_id=self.kwargs['assignment_id'])
                .select_related('assignment')
                .order_by())


class StudentAssignmentAssigneeUpdate(UpdateAPIView):
    permission_classes = [EditStudentAssignment]
    serializer_class = StudentAssignmentAssigneeSerializer
    lookup_url_kwarg = 'student_id'
    lookup_field = 'student_id'

    def get_queryset(self):
        return (StudentAssignment.objects
                .filter(assignment_id=self.kwargs['assignment_id'])
                .select_related('assignment__course')
                .order_by())
