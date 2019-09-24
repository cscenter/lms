from django.conf import settings
from django.db.models import Prefetch
from django.http import HttpResponseRedirect
from django.utils.translation import pgettext_lazy
from django.views import View
from django_filters.views import FilterMixin
from rest_framework.renderers import JSONRenderer
from vanilla import TemplateView

from core.exceptions import Redirect
from core.urls import reverse
from courses.constants import SemesterTypes
from courses.models import Course
from courses.utils import get_term_index, get_current_term_pair, \
    first_term_in_academic_year, get_term_by_index
from my_compscicenter_ru.api.serializers import CoursesSerializer
from my_compscicenter_ru.filters import CoursesFilter
from my_compscicenter_ru.utils import PublicRouteException, PublicRoute, \
    group_terms_by_academic_year
from users.models import User


class IndexView(View):
    def get(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            redirect_to = reverse('auth:login')
        else:
            redirect_to = user.get_absolute_url(
                subdomain=settings.LMS_SUBDOMAIN)
        if user.index_redirect:
            try:
                section_code = user.index_redirect
                redirect_to = PublicRoute.url_by_code(section_code)
            except PublicRouteException:
                pass
        elif user.is_curator:
            redirect_to = reverse('staff:student_search')
        elif user.is_teacher:
            redirect_to = reverse('teaching:assignment_list')
        elif user.is_student or user.is_volunteer:
            redirect_to = reverse('study:assignment_list')
        return HttpResponseRedirect(redirect_to=redirect_to)


class CourseOfferingsView(FilterMixin, TemplateView):
    filterset_class = CoursesFilter
    template_name = "my_compscicenter_ru/course_offerings.html"

    def get_queryset(self):
        prefetch_teachers = Prefetch(
            'teachers',
            queryset=User.objects.only("id", "first_name", "last_name",
                                       "patronymic"))
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
                .prefetch_related(prefetch_teachers)
                .order_by('-semester__year', '-semester__index',
                          'meta_course__name')
                .exclude(semester__type=SemesterTypes.SUMMER))

    def get_context_data(self, **kwargs):
        filterset_class = self.get_filterset_class()
        filterset = self.get_filterset(filterset_class)
        if not filterset.is_valid():
            raise Redirect(to=reverse("course_list"))
        term_options = {
            SemesterTypes.AUTUMN: pgettext_lazy("adjective", "autumn"),
            SemesterTypes.SPRING: pgettext_lazy("adjective", "spring"),
        }
        courses = filterset.qs
        terms = group_terms_by_academic_year(courses)
        active_academic_year, active_type = self.get_term(filterset, courses)
        if active_type == SemesterTypes.SPRING:
            active_year = active_academic_year + 1
        else:
            active_year = active_academic_year
        active_slug = "{}-{}".format(active_year, active_type)
        active_branch = filterset.data['branch']
        serializer = CoursesSerializer(courses)
        courses = serializer.data
        context = {
            "TERM_TYPES": term_options,
            "branches": filterset.form.fields['branch'].choices,
            "terms": terms,
            "courses": courses,
            "active_branch": active_branch,
            "active_academic_year": active_academic_year,
            "active_type": active_type,
            "active_slug": active_slug,
            "json": JSONRenderer().render({
                "branch": filterset.data['branch'],
                "initialFilterState": {
                    "academicYear": active_academic_year,
                    "selectedTerm": active_type,
                    "termSlug": active_slug
                },
                "terms": terms,
                "termOptions": term_options,
                "courses": courses
            }).decode('utf-8'),
        }
        return context

    def get_term(self, filters, courses):
        # Not sure this is the best place for this method
        assert filters.is_valid()
        if "semester" in filters.data:
            valid_slug = filters.data["semester"]
            term_year, term_type = valid_slug.split("-")
            term_year = int(term_year)
        else:
            # By default, return academic year and term type for the latest
            # available course.
            if courses:
                # Note: may hit db if `filters.qs` is not cached
                term = courses[0].semester
                term_year = term.year
                term_type = term.type
            else:
                term_year, term_type = get_current_term_pair()
        idx = first_term_in_academic_year(term_year, term_type)
        academic_year, _ = get_term_by_index(idx)
        return academic_year, term_type
