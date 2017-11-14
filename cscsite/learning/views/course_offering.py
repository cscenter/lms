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
from vanilla import DeleteView, UpdateView, CreateView

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
from learning.viewmixins import TeacherOnlyMixin, CuratorOnlyMixin
from learning.views.utils import get_co_from_query_params, \
    get_student_city_code, get_user_city_code

__all__ = ['CourseOfferingDetailView', 'CourseOfferingEditView',
           'CourseOfferingNewsCreateView', 'CourseOfferingNewsUpdateView',
           'CourseOfferingNewsDeleteView']


logger = logging.getLogger(__name__)


class CourseOfferingDetailView(generic.DetailView):
    model = CourseOffering
    context_object_name = 'course_offering'
    template_name = "learning/courseoffering_detail.html"
    default_tab = "about"

    def get(self, request, *args, **kwargs):
        # Validate GET-params
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
        self.object = self.get_object()
        # Can redirect to login if tab not available for authenticated user
        context = self.get_context_data(object=self.object)
        # Redirect to club if course was created before center establishment.
        co = context[self.context_object_name]
        if settings.SITE_ID == settings.CENTER_SITE_ID and co.is_open:
            index = get_term_index(CENTER_FOUNDATION_YEAR,
                                   SEMESTER_TYPES.autumn)
            if co.semester.index < index:
                url = get_club_domain(co.city.code) + co.get_absolute_url()
                return HttpResponseRedirect(url)
        return self.render_to_response(context)

    def get_object(self, queryset=None):
        return get_object_or_404(self.get_queryset())

    def get_queryset(self):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        return (CourseOffering.objects
                .in_city(self.request.city_code)
                .filter(semester__type=semester_type,
                        semester__year=year,
                        course__slug=self.kwargs['course_slug'])
                .select_related('course', 'semester')
                .prefetch_related(
                    Prefetch(
                        'courseofferingteacher_set',
                        queryset=(CourseOfferingTeacher
                                  .objects
                                  .select_related("teacher")
                                  .prefetch_related("teacher__groups")),
                        to_attr='course_teachers'
                    ),
                ))

    def get_context_data(self, *args, **kwargs):
        co = self.object
        user = self.request.user
        student_enrollment = user.enrollment_in_the_course(co.pk)
        is_enrolled = student_enrollment is not None
        co_failed_by_student = co.failed_by_student(
            user, enrollment=student_enrollment)
        # `.course_teachers` attached in queryset
        teachers_ids = (co.teacher_id for co in co.course_teachers)
        is_actual_teacher = user.pk in teachers_ids
        assignments = self.get_assignments(is_actual_teacher, is_enrolled,
                                           co_failed_by_student)
        course_reviews = co.enrollment_is_open and list(
            CourseOffering.objects
                .defer("description")
                .select_related("semester")
                .filter(course=co.course_id,
                        semester__index__lt=co.semester.index)
                .exclude(reviews__isnull=True)
                .exclude(reviews__exact='')
                .order_by("-semester__index"))
        teachers_by_role = CourseOfferingTeacher.grouped(co.course_teachers)
        # Aggregate teachers contacts
        contacts = [ct for g in teachers_by_role.values() for ct in g
                    if len(ct.teacher.private_contacts.strip()) > 0]
        # Course available for enrollment based on student city
        context = {
            'course_offering': co,
            'user_city': get_user_city_code(self.request),
            'co_failed_by_student': co_failed_by_student,
            'is_enrolled': is_enrolled,
            'is_actual_teacher': is_actual_teacher,
            'assignments': assignments,
            'news': co.courseofferingnews_set.all(),
            'classes': self.get_classes(co),
            'course_reviews': course_reviews,
            'teachers': teachers_by_role,
            'contacts': contacts,
        }
        # Tab name should be already validated in url pattern.
        active_tab_name = self.kwargs.get('tab', self.default_tab)
        pane = self.make_tabbed_pane(context)
        active_tab = pane[active_tab_name]
        if not active_tab.exist():
            raise Http404
        elif not active_tab.visible:
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        context["tabs"] = pane
        context["active_tab"] = active_tab_name
        return context

    def make_tabbed_pane(self, c):
        """Generate tabs list based on context"""
        pane = TabbedPane()
        u = self.request.user
        co = self.object

        def get_news_cnt():
            return (CourseOfferingNewsNotification.unread
                    .filter(course_offering_news__course_offering=co, user=u)
                    .count())
        unread_news_cnt = ((c.get("is_enrolled") or c.get('is_actual_teacher'))
                           and c.get("news") and get_news_cnt())
        can_view_assignments = (u.is_student or u.is_graduate or u.is_curator or
                                c['is_actual_teacher'] or c['is_enrolled'])
        can_view_news = (not c['co_failed_by_student'] and
                         ((u.is_authenticated and
                           u.status != STUDENT_STATUS.expelled) or
                          is_club_site()))
        tabs = [
            Tab("about", pgettext_lazy("course-tab", "About"),
                exist=lambda: True, visible=True),
            Tab("contacts", pgettext_lazy("course-tab", "Contacts"),
                exist=lambda: c['contacts'],
                visible=(c['is_enrolled'] or u.is_curator) and c['contacts']),
            # Note: reviews `exist` until enrollment is open
            Tab("reviews", pgettext_lazy("course-tab", "Reviews"),
                exist=lambda: c['course_reviews'],
                visible=(u.is_student or u.is_curator) and c['course_reviews']),
            Tab("classes", pgettext_lazy("course-tab", "Classes"),
                exist=lambda: c['classes'],
                visible=c['classes']),
            Tab("assignments", pgettext_lazy("course-tab", "Assignments"),
                exist=lambda: c['assignments'],
                visible=can_view_assignments and c['assignments']),
            Tab("news", pgettext_lazy("course-tab", "News"),
                exist=lambda: c['news'],
                visible=can_view_news and c['news'],
                unread_cnt=unread_news_cnt)
        ]
        for t in tabs:
            pane.add(t)
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

    def get_assignments(self, is_actual_teacher: bool, is_enrolled: bool,
                        co_failed_by_student: bool) -> List[Assignment]:
        """
        Build text-only list of course assignments or with links based on user
        enrollment.
        If course completed and student was enrolled on it - show links to
        passed assignments only.
        """
        user = self.request.user
        assignments_qs = (self.object.assignment_set
                          .only("title", "course_offering_id", "is_online",
                                "deadline_at")
                          .prefetch_related("assignmentattachment_set")
                          .order_by('deadline_at', 'title'))
        # Prefetch progress on assignments for authenticated student
        if is_enrolled:
            assignments_qs = assignments_qs.prefetch_related(
                Prefetch(
                    "studentassignment_set",
                    queryset=(StudentAssignment.objects
                            .filter(student=user)
                            .only("pk", "assignment_id", "grade")
                            .annotate(student_comments_cnt=Count(Case(
                                When(assignmentcomment__author_id=user.pk,
                                     then=Value(1)),
                                output_field=IntegerField())))
                            .order_by("pk"))  # optimize by setting order
                )
            )
        assignments = assignments_qs.all()
        for a in assignments:
            to_details = None
            if is_actual_teacher or user.is_curator:
                to_details = reverse("assignment_detail_teacher", args=[a.pk])
            elif is_enrolled:
                a_s = a.studentassignment_set.first()
                if a_s is not None:
                    # Hide link if student didn't try to solve assignment
                    # in completed course. No comments and grade => no attempt
                    if (co_failed_by_student and
                            not a_s.student_comments_cnt and
                            (a_s.grade is None or a_s.grade == 0)):
                        continue
                    to_details = a_s.get_student_url()
                else:
                    logger.error("can't find StudentAssignment for "
                                 "student ID {0}, assignment ID {1}"
                                 .format(user.pk, a.pk))
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
