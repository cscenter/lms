from django.conf import settings
from django.db.models import Prefetch
from django.http import HttpResponseBadRequest
from django.utils.timezone import now
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from courses.constants import SemesterTypes
from courses.models import Course, CourseTeacher, MetaCourse
from courses.utils import get_term_index
from users.constants import Roles
from users.models import User
from .serializers import TeacherCourseSerializer, TeacherSerializer, \
    CourseVideoSerializer


class TeacherCourseList(ListAPIView):
    pagination_class = None
    serializer_class = TeacherCourseSerializer

    def get_queryset(self):
        return (Course.objects
                .filter(is_open=False)
                .exclude(semester__type=SemesterTypes.SUMMER)
                .select_related("meta_course")
                .only("meta_course_id", "meta_course__name")
                .order_by("meta_course__name")
                .distinct("meta_course__name"))


class LecturerList(ListAPIView):
    """Returns lecturers"""
    pagination_class = None
    serializer_class = TeacherSerializer

    def get_queryset(self):
        lecturer = CourseTeacher.roles.lecturer
        queryset = (User.objects
                    .has_role(Roles.TEACHER)
                    .filter(courseteacher__roles=lecturer)
                    .select_related('branch')
                    .only("pk", "first_name", "last_name", "patronymic",
                          "cropbox_data", "photo", "branch__code", "gender",
                          "workplace")
                    .distinct())
        course = self.request.query_params.get('course', None)
        if course:
            term_index = get_term_index(settings.CENTER_FOUNDATION_YEAR,
                                        SemesterTypes.AUTUMN)
            queryset = queryset.filter(
                courseteacher__course__meta_course_id=course,
                courseteacher__course__semester__index__gte=term_index)
        queryset = queryset.prefetch_related(
            Prefetch(
                "courseteacher_set",
                queryset=(CourseTeacher.objects
                          .select_related("course",
                                          "course__semester")
                          .only("teacher_id",
                                "course__meta_course_id",
                                "course__semester__index")
                          .order_by("teacher_id", "course__meta_course__id",
                                    "-course__semester__index")
                          .distinct("teacher_id", "course__meta_course__id"))
            )

        )

        return queryset

    def list(self, request, *args, **kwargs):
        try:
            course = self.request.query_params.get('course', None)
            if course:
                course = int(course)
        except ValueError:
            return HttpResponseBadRequest()
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CourseVideoList(ListAPIView):
    pagination_class = None
    serializer_class = CourseVideoSerializer

    def get_queryset(self):
        lecturers = CourseTeacher.lecturers_prefetch()
        return (Course.objects
                .filter(is_published_in_video=True,
                        # Could be incorrect within one day since it doesn't
                        # check timezone
                        completed_at__lte=now().date(),
                        is_open=False)
                .order_by('-semester__year', 'semester__type')
                .select_related('meta_course', 'semester', 'branch')
                .prefetch_related(lecturers))
