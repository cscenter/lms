import datetime
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db import transaction, IntegrityError
from django.db.models import Prefetch
from django.http import HttpResponseBadRequest, HttpResponseRedirect, Http404, \
    HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect

from django.urls import reverse, NoReverseMatch, reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from vanilla import DetailView, CreateView, UpdateView, DeleteView

from core.exceptions import Redirect
from core.settings.base import CENTER_FOUNDATION_YEAR
from core.utils import get_club_domain, is_club_site
from core.views import ProtectedFormMixin
from courses.forms import CourseEditDescrForm, CourseNewsForm, CourseForm, \
    CourseClassForm
from courses.models import Course, CourseTeacher, CourseNews, MetaCourse, \
    CourseClass, CourseClassAttachment
from courses.settings import SemesterTypes
from courses.tabs import CourseInfoTab, get_course_tab_list, TabNotFound
from courses.utils import get_term_index, get_co_from_query_params
from learning.models import CourseNewsNotification
from users.mixins import TeacherOnlyMixin, CuratorOnlyMixin
from users.utils import get_user_city_code


class MetaCourseDetailView(generic.DetailView):
    model = MetaCourse
    template_name = "courses/meta_detail.html"
    context_object_name = 'meta_course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        courses = (Course.objects
                   .select_related("meta_course", "semester", "city")
                   .filter(meta_course=self.object))
        # Separate by city only on compsciclub.ru
        if is_club_site():
            courses = courses.in_city(self.request.city_code)
        else:
            courses = courses.in_center_branches()
        context['courses'] = courses
        context["show_city"] = not is_club_site()
        return context


class MetaCourseUpdateView(CuratorOnlyMixin, ProtectedFormMixin,
                           generic.UpdateView):
    model = MetaCourse
    template_name = "courses/simple_crispy_form.html"
    form_class = CourseForm

    def is_form_allowed(self, user, obj):
        return user.is_authenticated and user.is_curator


class CourseDetailView(DetailView):
    model = Course
    template_name = "courses/course_detail.html"
    context_object_name = 'course'

    def get(self, request, *args, **kwargs):
        # FIXME: separate `semester_slug` on route url lvl?
        try:
            year, _ = self.kwargs['semester_slug'].split("-", 1)
            _ = int(year)
        except ValueError:
            return HttpResponseBadRequest()
        # Redirects old style links
        if "tab" in request.GET:
            url_params = dict(self.kwargs)
            try:
                tab_name = request.GET["tab"]
                url = reverse("course_detail_with_active_tab",
                              kwargs={**url_params, "tab": tab_name})
            except NoReverseMatch:
                url = reverse("course_detail", kwargs=url_params)
            return HttpResponseRedirect(url)
        # Redirects to login page if tab is not visible to authenticated user
        context = self.get_context_data()
        # Redirects to club if course was created before center establishment.
        co = context[self.context_object_name]
        if settings.SITE_ID == settings.CENTER_SITE_ID and co.is_open:
            index = get_term_index(CENTER_FOUNDATION_YEAR,
                                   SemesterTypes.AUTUMN)
            if co.semester.index < index:
                url = get_club_domain(co.city.code) + co.get_absolute_url()
                return HttpResponseRedirect(url)
        return self.render_to_response(context)

    def get_context_data(self, *args, **kwargs):
        co = self.get_object()
        request_user = self.request.user
        teachers_by_role = co.get_grouped_teachers()
        # For correspondence course try to override timezone
        tz_override = None
        if (not co.is_actual_teacher(request_user) and co.is_correspondence
                and request_user.city_code):
            tz_override = settings.TIME_ZONES[request_user.city_id]
        # TODO: set default value if `tz_override` is None
        request_user_enrollment = request_user.get_enrollment(co.pk)
        is_actual_teacher = co.is_actual_teacher(request_user)
        # Attach unread notifications count if request user in mailing list
        # FIXME: Перенести в модель User или пусть эту инфу дёргает таба?
        unread_news = None
        if request_user_enrollment or is_actual_teacher:
            unread_news = (CourseNewsNotification.unread
                           .filter(course_offering_news__course=co,
                                   user=request_user)
                           .count())
        context = {
            'course': co,
            'user_city': get_user_city_code(self.request),
            'tz_override': tz_override,
            'teachers': teachers_by_role,
            'request_user_enrollment': request_user_enrollment,
            # TODO: move to user method
            'is_actual_teacher': is_actual_teacher,
            'unread_news': unread_news,
            'course_tabs': self.make_tabs(co)
        }
        return context

    def get_object(self):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        qs = (Course.objects
              .filter(semester__type=semester_type,
                      semester__year=year,
                      meta_course__slug=self.kwargs['course_slug'])
              .in_city(self.request.city_code)
              .select_related('meta_course', 'semester', 'city')
              .prefetch_related(
                    Prefetch(
                        'course_teachers',
                        queryset=(CourseTeacher.objects
                                  .select_related("teacher")))))
        return get_object_or_404(qs)

    def make_tabs(self, course: Course):
        tab_list = get_course_tab_list(self.request, course)
        try:
            show_tab = self.kwargs.get('tab', CourseInfoTab.type)
            tab_list.set_active_tab(show_tab)
        except TabNotFound:
            login_page = redirect_to_login(self.request.get_full_path())
            raise Redirect(to=login_page)
        return tab_list


class CourseEditView(TeacherOnlyMixin, ProtectedFormMixin,
                     generic.UpdateView):
    model = Course
    template_name = "courses/simple_crispy_form.html"
    form_class = CourseEditDescrForm

    def get_object(self, queryset=None):
        try:
            year, semester_type = self.kwargs['semester_slug'].split("-", 1)
            year = int(year)
        except ValueError:
            raise Http404

        if queryset is None:
            queryset = self.get_queryset()

        return get_object_or_404(
            queryset.filter(semester__type=semester_type,
                            semester__year=year,
                            meta_course__slug=self.kwargs['course_slug']))

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

    def get_queryset(self):
        return Course.objects.in_city(self.request.city_code)


class CourseNewsCreateView(TeacherOnlyMixin, CreateView):
    model = CourseNews
    template_name = "courses/simple_crispy_form.html"
    form_class = CourseNewsForm

    def get_form(self, **kwargs):
        form_class = self.get_form_class()
        co = get_co_from_query_params(self.kwargs, self.request.city_code)
        if not co:
            raise Http404('Course not found')
        if not self.is_form_allowed(self.request.user, co):
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        kwargs["course"] = co
        return form_class(**kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.author = self.request.user
        try:
            # Try to create news and notifications
            with transaction.atomic():
                self.object.save()
            messages.success(self.request, _("News was successfully created"),
                             extra_tags='timeout')
        except IntegrityError:
            messages.error(self.request, _("News wasn't created. Try again."))
        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.object.course.get_url_for_tab("news")

    def is_form_allowed(self, user, course: Course):
        return user.is_curator or user in course.teachers.all()


class CourseNewsUpdateView(TeacherOnlyMixin, ProtectedFormMixin,
                           UpdateView):
    model = CourseNews
    template_name = "courses/simple_crispy_form.html"
    form_class = CourseNewsForm

    def get_success_url(self):
        return self.object.course.get_url_for_tab("news")

    def is_form_allowed(self, user, obj: CourseNews):
        return user.is_curator or user in obj.course.teachers.all()


class CourseNewsDeleteView(TeacherOnlyMixin, ProtectedFormMixin,
                           DeleteView):
    model = CourseNews
    template_name = "forms/simple_delete_confirmation.html"

    def get_success_url(self):
        """
        Since we don't check was it the last deleted news or not - redirect to
        default active tab.
        """
        return self.object.course.get_absolute_url()

    def is_form_allowed(self, user, obj: CourseNews):
        return user.is_curator or user in obj.course.teachers.all()


class CourseClassDetailView(generic.DetailView):
    model = CourseClass
    context_object_name = 'course_class'
    template_name = "courses/course_class_detail.html"

    def get_queryset(self):
        return (CourseClass.objects
                .select_related("course",
                                "course__meta_course",
                                "course__semester",
                                "venue")
                .in_city(self.request.city_code))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['is_actual_teacher'] = (
            self.request.user.is_authenticated and
            self.request.user in (self.object
                                  .course
                                  .teachers.all()))
        context['attachments'] = self.object.courseclassattachment_set.all()
        return context


class CourseClassCreateUpdateMixin:
    def get_course(self):
        return get_co_from_query_params(self.kwargs, self.request.city_code)

    def get_form(self, **kwargs):
        course = self.get_course()
        if not course:
            raise Http404('Course not found')
        if not self.is_form_allowed(self.request.user, course):
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        kwargs["course"] = course
        kwargs["initial"] = self.get_initial(**kwargs)
        return CourseClassForm(**kwargs)

    @staticmethod
    def is_form_allowed(user, course):
        return user.is_curator or user in course.teachers.all()

    def get_initial(self, **kwargs):
        return None

    # TODO: add atomic
    def form_valid(self, form):
        self.object = form.save()
        attachments = self.request.FILES.getlist('attachments')
        if attachments:
            for attachment in attachments:
                CourseClassAttachment(course_class=self.object,
                                      material=attachment).save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return_url = self.request.GET.get('back')
        if return_url == 'timetable':
            return reverse('timetable_teacher')
        if return_url == 'course':
            return self.object.course.get_absolute_url()
        if return_url == 'calendar':
            return reverse('calendar_teacher')
        elif "_addanother" in self.request.POST:
            return self.object.course.get_create_class_url()
        else:
            return super().get_success_url()


class CourseClassCreateView(TeacherOnlyMixin,
                            CourseClassCreateUpdateMixin, CreateView):
    model = CourseClass
    template_name = "courses/course_class_form.html"

    def get_initial(self, **kwargs):
        # TODO: Add tests for initial data after discussion
        course = kwargs["course"]
        previous_class = (CourseClass.objects
                          .filter(course=course.pk)
                          .defer("description")
                          .order_by("-date", "starts_at")
                          .first())
        if previous_class is not None:
            return {
                "type": previous_class.type,
                "venue": previous_class.venue,
                "starts_at": previous_class.starts_at,
                "ends_at": previous_class.ends_at,
                "date": previous_class.date + datetime.timedelta(weeks=1)
            }
        return None

    def get_success_url(self):
        msg = _("The class '%s' was successfully created.")
        messages.success(self.request, msg % self.object.name,
                         extra_tags='timeout')
        return super().get_success_url()

    def post(self, request, *args, **kwargs):
        """Teachers can't add new classes if course already completed"""
        is_curator = self.request.user.is_curator
        co = self.get_course()
        if not co or (not is_curator and co.is_completed):
            return HttpResponseForbidden()
        form = self.get_form(data=request.POST, files=request.FILES, course=co)
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)


class CourseClassUpdateView(TeacherOnlyMixin,
                            CourseClassCreateUpdateMixin, UpdateView):
    model = CourseClass
    template_name = "courses/course_class_form.html"

    def get_success_url(self):
        msg = _("The class '%s' was successfully updated.")
        messages.success(self.request, msg % self.object.name,
                         extra_tags='timeout')
        return super().get_success_url()


class CourseClassAttachmentDeleteView(TeacherOnlyMixin, ProtectedFormMixin,
                                      DeleteView):
    model = CourseClassAttachment
    template_name = "forms/simple_delete_confirmation.html"

    def is_form_allowed(self, user, obj):
        return (user.is_curator or
                user in obj.course_class.course.teachers.all())

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        # TODO: move to model method
        os.remove(self.object.material.path)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return self.object.course_class.get_update_url()


class CourseClassDeleteView(TeacherOnlyMixin, ProtectedFormMixin,
                            DeleteView):
    model = CourseClass
    template_name = "forms/simple_delete_confirmation.html"
    success_url = reverse_lazy('timetable_teacher')

    def is_form_allowed(self, user, obj: CourseClass):
        return user.is_curator or user in obj.course.teachers.all()
