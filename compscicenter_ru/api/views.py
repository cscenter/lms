from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from django.conf import settings
from django.db.models import Prefetch, Q
from django.http import HttpResponseBadRequest
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from api.pagination import StandardPagination
from api.views import APIBaseView
from core.models import Branch
from courses.constants import SemesterTypes
from courses.models import Course, CourseTeacher
from courses.selectors import course_teachers_prefetch_queryset, get_lecturers
from courses.utils import get_term_index
from learning.models import GraduateProfile
from study_programs.models import AcademicDiscipline
from users.constants import Roles
from users.models import User

from .filters import AlumniFilter, CoursesPublicFilter
from .selectors import teachers_list
from .serializers import (
    AlumniSerializer, CoursePublicSerializer, CourseVideoSerializer,
    SiteCourseSerializer, TeacherSerializer, TestimonialCardSerializer
)


class SiteCourseList(ListAPIView):
    pagination_class = None
    serializer_class = SiteCourseSerializer

    def get_queryset(self):
        return (Course.objects
                .filter(main_branch__site_id=settings.SITE_ID,
                        main_branch__active=True)
                .exclude(semester__type=SemesterTypes.SUMMER)
                .select_related("meta_course")
                .only("meta_course_id", "meta_course__name")
                .order_by("meta_course__name")
                .distinct("meta_course__name"))


class TeacherList(APIBaseView):
    """Returns all teachers except pure reviewers or spectators"""
    pagination_class = None

    def get(self, request, *args, **kwargs):
        try:
            course = request.query_params.get('course', None)
            if course:
                course = int(course)
        except ValueError:
            return HttpResponseBadRequest()
        teachers = teachers_list(site=self.request.site, course=course)
        serializer = TeacherSerializer(teachers, many=True)
        return Response(serializer.data)


class CourseVideoList(ListAPIView):
    pagination_class = None
    serializer_class = CourseVideoSerializer

    def get_queryset(self):
        lecturers = Prefetch('course_teachers', queryset=get_lecturers())
        return (Course.objects
                .filter(is_published_in_video=True,
                        # Could be incorrect within one day since it doesn't
                        # check timezone
                        completed_at__lte=now().date(),
                        main_branch__site_id=settings.SITE_ID,
                        main_branch__active=True)
                .order_by('-semester__year', 'semester__type')
                .select_related('meta_course', 'semester', 'main_branch')
                .prefetch_related(lecturers))


class AlumniList(ListAPIView):
    """Retrieves data for alumni/ page"""
    pagination_class = None
    serializer_class = AlumniSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = AlumniFilter

    def get_queryset(self):
        return (GraduateProfile.active
                .get_only_required_fields()
                .prefetch_related("academic_disciplines")
                .order_by("-graduation_year",
                          "student_profile__user__last_name",
                          "student_profile__user__first_name"))

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = {
            "data": serializer.data,
            "cities": {
                "spb": _("Saint Petersburg"),
                "nsk": _("Novosibirsk")
            },
        }
        return Response(data)


class TestimonialList(ListAPIView):
    # FIXME: Add index for pagination if limit/offset is too slow
    pagination_class = StandardPagination
    serializer_class = TestimonialCardSerializer

    def get_queryset(self):
        site_branches = Branch.objects.for_site(settings.SITE_ID, all=True)
        return (GraduateProfile.active
                .filter(student_profile__branch__in=site_branches)
                .with_testimonial()
                .get_only_required_fields()
                .prefetch_related("academic_disciplines")
                .order_by("-graduation_year", "pk"))

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        areas = {a.pk: a.name for a in AcademicDiscipline.objects.all()}
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
    filterset_class = CoursesPublicFilter
    serializer_class = CoursePublicSerializer

    def get_queryset(self):
        course_teachers = Prefetch('course_teachers',
                                   queryset=course_teachers_prefetch_queryset())
        return (Course.objects
                .exclude(semester__type=SemesterTypes.SUMMER)
                .select_related('meta_course', 'semester', 'main_branch')
                .only("pk", "main_branch_id", "grading_type",
                      "public_videos_count", "public_slides_count",
                      "public_attachments_count",
                      "meta_course__name", "meta_course__slug",
                      "semester__year", "semester__index", "semester__type",
                      "main_branch__code", "main_branch__site_id")
                .prefetch_related(course_teachers)
                .order_by('-semester__year', '-semester__index',
                          'meta_course__name')
                )
