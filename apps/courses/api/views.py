from django.db.models import Prefetch
from django.http import HttpResponseBadRequest
from django.utils.timezone import now
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from core.settings.base import CENTER_FOUNDATION_YEAR
from courses.api.serializers import MetaCourseSerializer, TeacherSerializer, \
    CourseVideoSerializer
from courses.models import Course, CourseTeacher
from courses.constants import SemesterTypes
from courses.utils import get_term_index
from users.constants import Roles
from users.models import User

# FIXME: replace with base implementation (both for CS club ans CS center [TODO: remove is_open=False, etc), then subclass
class CourseList(ListAPIView):
    """Returns courses for CS Center"""
    pagination_class = None
    serializer_class = MetaCourseSerializer

    def get_queryset(self):
        return (Course.objects
                .filter(is_open=False)
                .exclude(semester__type=SemesterTypes.SUMMER)
                .select_related("meta_course")
                .only("meta_course_id", "meta_course__name", "semester__index")
                .order_by("meta_course__name")
                .distinct("meta_course__name"))


class LecturerList(ListAPIView):
    """Returns list of CS Center lecturers"""
    pagination_class = None
    serializer_class = TeacherSerializer

    def get_queryset(self):
        lecturer = CourseTeacher.roles.lecturer
        queryset = (User.objects
                    .has_role(Roles.TEACHER)
                    .filter(courseteacher__roles=lecturer)
                    .only("pk", "first_name", "last_name", "patronymic",
                          "cropbox_data", "photo", "city_id", "gender",
                          "workplace")
                    .distinct())
        course = self.request.query_params.get('course', None)
        if course:
            term_index = get_term_index(CENTER_FOUNDATION_YEAR,
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
                        completed_at__lte=now().date())
                .in_center_branches()
                .order_by('-semester__year', 'semester__type')
                .select_related('meta_course', 'semester')
                .prefetch_related(lecturers))
