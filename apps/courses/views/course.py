from django.contrib.auth.views import redirect_to_login
from django.db.models import Prefetch
from django.views import generic
from vanilla import DetailView

from core.exceptions import Redirect
from core.utils import is_club_site
from core.views import ProtectedFormMixin
from courses.constants import TeacherRoles
from courses.forms import CourseEditDescrForm
from courses.models import Course, CourseTeacher
from courses.permissions import can_view_private_materials
from courses.services import group_teachers
from courses.tabs import get_course_tab_list, CourseInfoTab, TabNotFound
from courses.views.mixins import CourseURLParamsMixin
from learning.models import CourseNewsNotification
from learning.permissions import course_access_role
from users.mixins import TeacherOnlyMixin

__all__ = ('CourseDetailView', 'CourseEditView')


class CourseDetailView(CourseURLParamsMixin, DetailView):
    model = Course
    template_name = "courses/course_detail.html"
    context_object_name = 'course'

    def get_course_queryset(self):
        course_teachers = Prefetch('course_teachers',
                                   queryset=(CourseTeacher.objects
                                             .select_related("teacher")
                                             .order_by('teacher__last_name',
                                                       'teacher__first_name')))
        return (super().get_course_queryset()
                .select_related('meta_course', 'semester', 'branch')
                .prefetch_related(course_teachers,
                                  "additional_branches"))

    def get_object(self):
        return self.course

    def get_context_data(self, *args, **kwargs):
        course = self.course
        # Tabs
        tab_list = get_course_tab_list(self.request, course)
        try:
            show_tab = self.kwargs.get('tab', CourseInfoTab.type)
            tab_list.set_active_tab(show_tab)
        except TabNotFound:
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        # Teachers
        by_role = group_teachers(course.course_teachers.all())
        teachers = {'main': [], 'others': []}
        for role, ts in by_role.items():
            if role in (TeacherRoles.LECTURER, TeacherRoles.SEMINAR):
                group = 'main'
            else:
                group = 'others'
            teachers[group].extend(ts)
        role = course_access_role(course=course, user=self.request.user)
        context = {
            'course': course,
            'course_tabs': tab_list,
            'teachers': teachers,
            'has_access_to_private_materials': can_view_private_materials(role),
            **self._get_additional_context(course)
        }
        return context

    def _get_additional_context(self, course, **kwargs):
        request_user = self.request.user
        is_actual_teacher = course.is_actual_teacher(request_user.pk)
        # For correspondence course try to override timezone
        tz_override = None
        # FIXME: cache additional branch count?
        if not is_actual_teacher and len(course.additional_branches.all()):
            tz_override = request_user.get_timezone()

        if request_user.has_perm("study.view_own_enrollments"):
            request_user_enrollment = request_user.get_enrollment(course.pk)
        else:
            request_user_enrollment = None
        # Attach unread notifications count if authenticated user is in
        # a mailing list
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
            'tz_override': tz_override,
            'request_user_enrollment': request_user_enrollment,
            'is_actual_teacher': is_actual_teacher,
            'unread_news': unread_news,
            'survey_url': survey_url,
        }


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
