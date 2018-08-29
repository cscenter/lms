import logging
from typing import List

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db import transaction, IntegrityError
from django.db.models import Q, Prefetch, When, Value, Case, \
    IntegerField, BooleanField, Count
from django.http import HttpResponseBadRequest, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, NoReverseMatch
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.views import generic
from rest_framework.generics import ListAPIView
from vanilla import DeleteView, UpdateView, CreateView, DetailView

from api.permissions import CuratorAccessPermission
from core.exceptions import Redirect
from core.utils import get_club_domain, is_club_site
from core.views import ProtectedFormMixin
from core.widgets import TabbedPane, Tab
from learning.forms import CourseOfferingEditDescrForm, CourseOfferingNewsForm
from learning.models import CourseOffering, CourseOfferingTeacher, \
    CourseOfferingNewsNotification, CourseClass, Assignment, StudentAssignment, \
    CourseOfferingNews
from learning.serializers import CourseOfferingNewsNotificationSerializer
from learning.settings import CENTER_FOUNDATION_YEAR, SEMESTER_TYPES, \
    STUDENT_STATUS
from learning.utils import get_term_index
from learning.viewmixins import TeacherOnlyMixin
from learning.views.utils import get_co_from_query_params, get_user_city_code

__all__ = ['CourseOfferingDetailView', 'CourseOfferingEditView',
           'CourseOfferingNewsCreateView', 'CourseOfferingNewsUpdateView',
           'CourseOfferingNewsDeleteView']


logger = logging.getLogger(__name__)


class CourseOfferingDetailView(DetailView):
    model = CourseOffering
    context_object_name = 'course_offering'
    template_name = "learning/courseoffering_detail.html"
    default_tab = "about"

    def get(self, request, *args, **kwargs):
        try:
            year, _ = self.kwargs['semester_slug'].split("-", 1)
            _ = int(year)
        except ValueError:
            return HttpResponseBadRequest()
        # Redirect old style links
        if "tab" in request.GET:
            url_params = dict(self.kwargs)
            try:
                tab_name = request.GET["tab"]
                url = reverse("course_offering_detail_with_active_tab",
                              kwargs={**url_params, "tab": tab_name})
            except NoReverseMatch:
                url = reverse("course_offering_detail", kwargs=url_params)
            return HttpResponseRedirect(url)
        # Can redirect to login if tab not available for authenticated user
        context = self.get_context_data()
        # Redirect to club if course was created before center establishment.
        co = context[self.context_object_name]
        if settings.SITE_ID == settings.CENTER_SITE_ID and co.is_open:
            index = get_term_index(CENTER_FOUNDATION_YEAR,
                                   SEMESTER_TYPES.autumn)
            if co.semester.index < index:
                url = get_club_domain(co.city.code) + co.get_absolute_url()
                return HttpResponseRedirect(url)
        return self.render_to_response(context)

    def get_context_data(self, *args, **kwargs):
        co = self.get_object()
        request_user = self.request.user
        request_user_enrollment = request_user.get_enrollment(co.pk)
        co_failed_by_student = (request_user_enrollment and
                                co.failed_by_student(request_user,
                                                     request_user_enrollment))
        teachers_by_role = co.get_grouped_teachers()
        # Aggregate teachers contacts
        contacts = [ct for g in teachers_by_role.values() for ct in g
                    if len(ct.teacher.private_contacts.strip()) > 0]
        # For correspondence course try to override timezone
        tz_override = None
        if (not co.is_actual_teacher(request_user) and co.is_correspondence
                and request_user.city_code):
            tz_override = settings.TIME_ZONES[request_user.city_id]
        # TODO: set default value if `tz_override` is None
        context = {
            'course_offering': co,
            'user_city': get_user_city_code(self.request),
            'tz_override': tz_override,
            'teachers': teachers_by_role,
            'co_failed_by_student': co_failed_by_student,
            # TODO: replace with request_user_enrollment
            'is_enrolled': request_user_enrollment is not None,
            'is_actual_teacher': co.is_actual_teacher(request_user),
            'course_reviews': co.enrollment_is_open and co.get_reviews(),
            'contacts': contacts,
            'classes': self.get_classes(co),
            'assignments': self.get_assignments(co, request_user_enrollment),
            'news': co.courseofferingnews_set.all(),
        }
        context["tabs"] = self.make_tabbed_pane(context)
        return context

    def get_object(self):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        qs = (CourseOffering.objects
              .filter(semester__type=semester_type,
                      semester__year=year,
                      course__slug=self.kwargs['course_slug'])
              .in_city(self.request.city_code)
              .select_related('course', 'semester')
              .prefetch_related(
                    Prefetch(
                        'courseofferingteacher_set',
                        queryset=(CourseOfferingTeacher.objects
                                  .select_related("teacher")
                                  .prefetch_related("teacher__groups")))))
        return get_object_or_404(qs)

    def make_tabbed_pane(self, c):
        """Tabs visibility depends on context"""
        pane = TabbedPane()
        u = self.request.user
        co = c['course_offering']

        def get_news_cnt():
            return (CourseOfferingNewsNotification.unread
                    .filter(course_offering_news__course_offering=co, user=u)
                    .count())

        unread_news_cnt = ((c.get("is_enrolled") or c.get('is_actual_teacher'))
                           and c.get("news") and get_news_cnt())
        can_view_assignments = (u.is_student or u.is_graduate or u.is_curator or
                                u.is_teacher or c['is_enrolled'])
        can_view_news = (not c['co_failed_by_student'] and
                         ((u.is_authenticated and
                           u.status != STUDENT_STATUS.expelled) or
                          is_club_site()))
        tabs = [
            Tab("about", pgettext_lazy("course-tab", "About"),
                exists=lambda: True,
                visible=True),
            Tab("contacts", pgettext_lazy("course-tab", "Contacts"),
                exists=lambda: len(c['contacts']) > 0,
                visible=c['is_enrolled'] or u.is_curator),
            # Note: reviews `exists` until enrollment is open
            Tab("reviews", pgettext_lazy("course-tab", "Reviews"),
                exists=lambda: len(c['course_reviews']) > 0,
                visible=u.is_student or u.is_curator),
            Tab("classes", pgettext_lazy("course-tab", "Classes"),
                exists=lambda: len(c['classes']) > 0,
                visible=True),
            Tab("assignments", pgettext_lazy("course-tab", "Assignments"),
                exists=lambda: len(c['assignments']) > 0,
                visible=can_view_assignments),
            Tab("news", pgettext_lazy("course-tab", "News"),
                exists=lambda: len(c['news']) > 0,
                visible=can_view_news,
                unread_cnt=unread_news_cnt)
        ]
        for t in tabs:
            pane.add(t)
        # Tab name have to be validated by url() pattern.
        show_tab = self.kwargs.get('tab', self.default_tab)
        tab_to_show = pane[show_tab]
        if not tab_to_show.exists():
            raise Http404
        elif not tab_to_show.visible:
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        pane.set_active_tab(tab_to_show)
        return pane

    @staticmethod
    def get_classes(course_offering) -> List[CourseClass]:
        """Get course classes with attached materials"""
        classes = []
        course_classes_qs = (course_offering.courseclass_set
            .select_related("venue")
            .annotate(attachments_cnt=Count('courseclassattachment'))
            .annotate(has_attachments=Case(
                When(attachments_cnt__gt=0, then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            ))
            .order_by("date", "starts_at"))
        for cc in course_classes_qs.iterator():
            class_url = cc.get_absolute_url()
            materials = []
            if cc.slides:
                materials.append({'url': class_url + "#slides",
                                  'name': _("Slides")})
            if cc.video_url:
                materials.append({'url': class_url + "#video",
                                  'name': _("video")})
            if cc.has_attachments:
                materials.append({'url': class_url + "#attachments",
                                  'name': _("Files")})
            other_materials_embed = (
                cc.other_materials.startswith(
                    ("<iframe src=\"https://www.slideshare",
                     "<iframe src=\"http://www.slideshare"))
                and cc.other_materials.strip().endswith("</iframe>"))
            if cc.other_materials and not other_materials_embed:
                materials.append({'url': class_url + "#other_materials",
                                  'name': _("CourseClass|Other [materials]")})
            for m in materials:
                m['name'] = m['name'].lower()
            materials_str = ", ".join(",&nbsp;"
                                      .join(("<a href={url}>{name}</a>"
                                             .format(**x))
                                            for x in materials[i:i + 2])
                                      for i in range(0, len(materials), 2))
            materials_str = materials_str or _("No")
            setattr(cc, 'materials_str', materials_str)
            classes.append(cc)
        return classes

    def get_assignments(self, co: CourseOffering,
                        request_user_enrollment) -> List[Assignment]:
        """
        For enrolled students show links to there submissions. If course
        is completed and student was enrolled in - show links to
        successfully passed assignments only.
        For course teachers (among all terms) show links to assignment details.
        For others show text only.
        """
        request_user = self.request.user
        co_failed_by_student = (request_user_enrollment and
                                co.failed_by_student(request_user,
                                                     request_user_enrollment))
        assignments = co.assignment_set.list()
        if request_user_enrollment is not None:
            assignments = assignments.with_progress(request_user)
        assignments = assignments.all()  # enable query caching
        for a in assignments:
            to_details = None
            if co.is_actual_teacher(request_user) or request_user.is_curator:
                to_details = reverse("assignment_detail_teacher", args=[a.pk])
            elif request_user_enrollment is not None:
                student_progress = a.studentassignment_set.first()
                if student_progress is not None:
                    # Hide link if student didn't try to solve assignment
                    # in completed course.
                    if (co_failed_by_student and
                            not student_progress.student_comments_cnt and
                            (student_progress.grade is None or student_progress.grade == 0)):
                        continue
                    to_details = student_progress.get_student_url()
                else:
                    logger.info(f"no StudentAssignment for student ID "
                                f"{request_user.pk}, assignment ID {a.pk}")
            setattr(a, 'magic_link', to_details)
        return assignments


# FIXME: Do I need ProtectedFormMixin?
class CourseOfferingEditView(TeacherOnlyMixin, ProtectedFormMixin,
                             generic.UpdateView):
    model = CourseOffering
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseOfferingEditDescrForm

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
                            course__slug=self.kwargs['course_slug']))

    def get_initial(self):
        """Keep in mind that `initial` overrides values from model dict"""
        initial = super().get_initial()
        # Note: In edit view we always have an object
        if not self.object.description_ru:
            initial["description_ru"] = self.object.course.description_ru
        if not self.object.description_en:
            initial["description_en"] = self.object.course.description_en
        return initial

    def is_form_allowed(self, user, obj):
        return user.is_curator or user in obj.teachers.all()

    def get_queryset(self):
        return CourseOffering.objects.in_city(self.request.city_code)


class CourseOfferingNewsCreateView(TeacherOnlyMixin, CreateView):
    model = CourseOfferingNews
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseOfferingNewsForm

    def get_form(self, **kwargs):
        form_class = self.get_form_class()
        co = get_co_from_query_params(self.kwargs, self.request.city_code)
        if not co:
            raise Http404('Course offering not found')
        if not self.is_form_allowed(self.request.user, co):
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        kwargs["course_offering"] = co
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
        return self.object.course_offering.get_url_for_tab("news")

    def is_form_allowed(self, user, course_offering):
        return user.is_curator or user in course_offering.teachers.all()


class CourseOfferingNewsUpdateView(TeacherOnlyMixin, ProtectedFormMixin,
                                   UpdateView):
    model = CourseOfferingNews
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseOfferingNewsForm

    def get_success_url(self):
        return self.object.course_offering.get_url_for_tab("news")

    def is_form_allowed(self, user, obj):
        return user.is_curator or user in obj.course_offering.teachers.all()


class CourseOfferingNewsDeleteView(TeacherOnlyMixin, ProtectedFormMixin,
                                   DeleteView):
    model = CourseOfferingNews
    template_name = "learning/simple_delete_confirmation.html"

    def get_success_url(self):
        """
        Since we don't check was it the last deleted news or not - redirect to
        default active tab.
        """
        return self.object.course_offering.get_absolute_url()

    def is_form_allowed(self, user, obj):
        return user.is_curator or user in obj.course_offering.teachers.all()


class CourseOfferingNewsUnreadNotificationsView(ListAPIView):
    permission_classes = [CuratorAccessPermission]
    serializer_class = CourseOfferingNewsNotificationSerializer

    def get_queryset(self):
        return (CourseOfferingNewsNotification.unread
                .filter(course_offering_news_id=self.kwargs.get('news_pk'))
                .select_related("user")
                .order_by("user__last_name"))
