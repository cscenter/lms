from django.conf import settings
from django.db.models import Prefetch
from django.http import HttpResponseBadRequest
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from api.pagination import StandardPagination
from learning.api.serializers import AlumniSerializer, TestimonialSerializer, \
    TeacherSerializer, CourseSerializer
from learning.models import AreaOfStudy
from courses.models import Course, Semester, CourseTeacher
from learning.settings import CENTER_FOUNDATION_YEAR
from courses.settings import SemesterTypes
from courses.utils import get_term_index
from users.models import User


class CourseList(ListAPIView):
    """Returns courses for CS Center"""
    pagination_class = None
    serializer_class = CourseSerializer

    def get_queryset(self):
        return (Course.objects
                .from_center_foundation()
                .select_related("meta_course")
                .exclude(semester__type=SemesterTypes.SUMMER)
                .filter(is_open=False)
                .only("meta_course_id", "meta_course__name", "semester__index")
                .order_by("meta_course__name")
                .distinct("meta_course__name"))


class TeacherList(ListAPIView):
    """Returns teachers for CS Center"""
    pagination_class = None
    serializer_class = TeacherSerializer

    def get_queryset(self):
        lecturer = CourseTeacher.roles.lecturer
        queryset = (User.objects
                    .filter(groups=User.roles.TEACHER_CENTER,
                            courseteacher__roles=lecturer)
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
                          .order_by("teacher_id", "course__meta_course__id")
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


class AlumniList(ListAPIView):
    """Retrieves data for alumni page"""
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
