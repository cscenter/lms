from django.conf import settings
from django.db.models import Prefetch
from django.http import HttpResponseBadRequest
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from api.pagination import StandardPagination
from courses.constants import SemesterTypes
from courses.models import Course, CourseTeacher
from courses.utils import get_term_index
from learning.models import GraduateProfile
from study_programs.models import AcademicDiscipline
from users.constants import Roles
from users.models import User
from .filters import CourseFilter
from .serializers import TeacherCourseSerializer, TeacherSerializer, \
    CourseVideoSerializer, AlumniSerializer, TestimonialCardSerializer, \
    CoursePublicSerializer


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
                    .distinct()
                    .order_by("last_name", "first_name"))
        course = self.request.query_params.get("course", None)
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


class CourseList(ListAPIView):
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = CourseFilter
    serializer_class = CoursePublicSerializer

    def get_queryset(self):
        prefetch_teachers = Prefetch(
            'course_teachers',
            queryset=(CourseTeacher.objects
                      .select_related('teacher')
                      .only('id', 'course_id', 'teacher_id',
                            'teacher__first_name',
                            'teacher__last_name',
                            'teacher__patronymic')))
        center_foundation_term_index = get_term_index(
            settings.CENTER_FOUNDATION_YEAR, SemesterTypes.AUTUMN)
        return (Course.objects
                .select_related('meta_course', 'semester', 'branch')
                .only("pk", "branch_id", "is_open", "grading_type",
                      "videos_count", "materials_slides", "materials_files",
                      "meta_course__name", "meta_course__slug",
                      "semester__year", "semester__index", "semester__type",
                      "branch__code")
                .filter(semester__index__gte=center_foundation_term_index)
                .exclude(semester__type=SemesterTypes.SUMMER)
                .prefetch_related(prefetch_teachers)
                .order_by('-semester__year', '-semester__index',
                          'meta_course__name')
                )
