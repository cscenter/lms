from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.db.models import Prefetch
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import NoReverseMatch
from django.views import generic
from vanilla import DetailView

from core.exceptions import Redirect
from core.settings.base import CENTER_FOUNDATION_YEAR
from core.urls import reverse
from core.utils import get_club_domain, is_club_site
from core.views import ProtectedFormMixin
from courses.forms import CourseEditDescrForm
from courses.models import Course, CourseTeacher
from courses.settings import SemesterTypes
from courses.tabs import get_course_tab_list, CourseInfoTab, TabNotFound
from courses.utils import get_term_index
from courses.views.mixins import CourseURLParamsMixin
from learning.models import CourseNewsNotification
from users.mixins import TeacherOnlyMixin
from users.utils import get_user_city_code

__all__ = ('CourseDetailView', 'CourseEditView')


# FIXME: разделить кастомную логику
class CourseDetailView(CourseURLParamsMixin, DetailView):
    model = Course
    template_name = "courses/course_detail.html"
    context_object_name = 'course'

    def get(self, request, *args, **kwargs):
        # Redirects old style link
        if "tab" in request.GET:
            try:
                tab_name = request.GET["tab"]
                url = reverse("course_detail_with_active_tab",
                              kwargs={**kwargs, "tab": tab_name})
            except NoReverseMatch:
                url = reverse("course_detail", kwargs=kwargs)
            return HttpResponseRedirect(url)
        # Redirects to login page if tab is not visible to authenticated user
        context = self.get_context_data()
        # Redirects to club if course was created before center establishment.
        co = context[self.context_object_name]
        if settings.SITE_ID == settings.CENTER_SITE_ID and co.is_open:
            index = get_term_index(CENTER_FOUNDATION_YEAR,
                                   SemesterTypes.AUTUMN)
            if co.semester.index < index:
                parsed = urlparse(co.get_absolute_url())
                url = get_club_domain(co.city.code) + parsed.path
                return HttpResponseRedirect(url)
        return self.render_to_response(context)

    def get_course_queryset(self):
        course_teachers = Prefetch('course_teachers',
                                   queryset=(CourseTeacher.objects
                                             .select_related("teacher")))
        return (super().get_course_queryset()
                .select_related('meta_course', 'semester', 'city')
                .prefetch_related(course_teachers))

    def get_object(self):
        return self.course

    def get_context_data(self, *args, **kwargs):
        course = self.course
        teachers_by_role = course.get_grouped_teachers()
        context = {
            'course': course,
            'course_tabs': self.make_tabs(course),
            'teachers': teachers_by_role,
            **self._get_additional_context(course)
        }
        return context

    def _get_additional_context(self, course, **kwargs):
        request_user = self.request.user
        # For correspondence course try to override timezone
        tz_override = None
        if (not course.is_actual_teacher(request_user) and course.is_correspondence
                and request_user.city_code):
            tz_override = settings.TIME_ZONES[request_user.city_id]
        # TODO: set default value if `tz_override` is None
        request_user_enrollment = request_user.get_enrollment(course.pk)
        is_actual_teacher = course.is_actual_teacher(request_user)
        # Attach unread notifications count if request user in mailing list
        unread_news = None
        if request_user_enrollment or is_actual_teacher:
            unread_news = (CourseNewsNotification.unread
                           .filter(course_offering_news__course=course,
                                   user=request_user)
                           .count())
        survey_url = course.survey_url
        if not survey_url and not is_club_site():
            from surveys.models import CourseSurvey
            cs = CourseSurvey.get_active(course)
            if cs:
                survey_url = cs.get_absolute_url(course=course)
        return {
            'user_city': get_user_city_code(self.request),
            'tz_override': tz_override,
            'request_user_enrollment': request_user_enrollment,
            # TODO: move to user method
            'is_actual_teacher': is_actual_teacher,
            'unread_news': unread_news,
            'survey_url': survey_url,
        }

    def make_tabs(self, course: Course):
        tab_list = get_course_tab_list(self.request, course)
        try:
            show_tab = self.kwargs.get('tab', CourseInfoTab.type)
            tab_list.set_active_tab(show_tab)
        except TabNotFound:
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        return tab_list


class CourseEditView(TeacherOnlyMixin, CourseURLParamsMixin, ProtectedFormMixin,
                     generic.UpdateView):
    model = Course
    template_name = "courses/simple_crispy_form.html"
    form_class = CourseEditDescrForm

    def get_object(self, queryset=None):
        return self.course

    def get_initial(self):
        """Keep in mind that `initial` overrides values from model dict"""
        initial = super().get_initial()
        # Note: In edit view we always have an object
        if not self.object.description_ru:
            initial["description_ru"] = self.object.meta_course.description_ru
        if not self.object.description_en:
            initial["description_en"] = self.object.meta_course.description_en
        return initial

    def is_form_allowed(self, user, obj):
        return user.is_curator or user in obj.teachers.all()
