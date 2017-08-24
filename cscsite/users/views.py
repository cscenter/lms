# -*- coding: utf-8 -*-

import json
from collections import OrderedDict

from braces.views import LoginRequiredMixin
from django.conf import settings
from django.contrib import auth
from django.db.models import Prefetch, Count
from django.http import HttpResponseRedirect, Http404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import is_safe_url
from django.views import generic
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from vanilla import DetailView

from core.views import ProtectedFormMixin
from learning.models import StudentAssignment, \
    CourseOffering, Semester, Enrollment, StudyProgram
from learning.settings import LEARNING_BASE, TEACHING_BASE, GRADES
from learning.viewmixins import CuratorOnlyMixin
from users.models import SHADCourseRecord
from .forms import LoginForm, UserProfileForm, CSCUserReferenceCreateForm
from .models import CSCUser, CSCUserReference


# inspired by https://raw2.github.com/concentricsky/django-sky-visitor/


class LoginView(generic.FormView):
    redirect_field_name = auth.REDIRECT_FIELD_NAME
    form_class = LoginForm
    template_name = "login.html"

    @method_decorator(never_cache)
    @method_decorator(sensitive_post_parameters('password'))
    def dispatch(self, *args, **kwargs):
        return super(LoginView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        # credentials were checked in AuthenticationForm.is_valid()
        auth.login(self.request, form.get_user())
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(LoginView, self).get_context_data(**kwargs)
        context["has_next"] = (self.redirect_field_name in self.request.POST
                               or self.redirect_field_name in self.request.GET)
        return context

    def get_success_url(self):
        redirect_to = self.request.GET.get(self.redirect_field_name)

        if not redirect_to:
            user_groups = self.request.user.get_cached_groups()
            if user_groups == {CSCUser.group.STUDENT_CENTER}:
                redirect_to = reverse(LEARNING_BASE)
            elif user_groups == {CSCUser.group.TEACHER_CENTER}:
                redirect_to = reverse(TEACHING_BASE)

        if not is_safe_url(redirect_to, self.request.get_host()):
            redirect_to = settings.LOGOUT_REDIRECT_URL

        return redirect_to

    def get(self, request, *args, **kwargs):
        self.request.session.set_test_cookie()
        return super(LoginView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            if self.request.session.test_cookie_worked():
                self.request.session.delete_test_cookie()
            return self.form_valid(form)
        else:
            self.request.session.set_test_cookie()
            return self.form_invalid(form)


class LogoutView(LoginRequiredMixin,
                 generic.RedirectView):
    redirect_field_name = auth.REDIRECT_FIELD_NAME

    def get(self, request, *args, **kwargs):
        # FIXME: enable after bugfix in django-loginas
        # restore_original_login(request)
        auth.logout(request)
        return super(LogoutView, self).get(request, *args, **kwargs)

    def get_redirect_url(self, **kwargs):
        redirect_to = settings.LOGOUT_REDIRECT_URL

        if self.redirect_field_name in self.request.GET:
            maybe_redirect_to = self.request.GET[self.redirect_field_name]
            if is_safe_url(url=maybe_redirect_to,
                           host=self.request.get_host()):
                redirect_to = maybe_redirect_to

        return redirect_to


class TeacherDetailView(DetailView):
    template_name = "users/teacher_detail.html"
    context_object_name = 'teacher'

    def get_queryset(self, *args, **kwargs):
        co_queryset = (CourseOffering.objects
                       .in_city(self.request.city_code)
                       .select_related('semester', 'course'))
        return (auth.get_user_model()._default_manager
            .prefetch_related(
            Prefetch('teaching_set',
                     queryset=co_queryset.all(),
                     to_attr='course_offerings')))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = context[self.context_object_name]
        if not teacher.is_teacher:
            raise Http404
        return context


class UserDetailView(generic.DetailView):
    template_name = "users/user_detail.html"
    context_object_name = 'profile_user'

    def get_queryset(self, *args, **kwargs):
        enrollment_queryset = Enrollment.active.select_related(
            'course_offering',
            'course_offering__semester',
            'course_offering__course'
        )
        if not self.request.user.is_authenticated:
            enrollment_queryset = enrollment_queryset.exclude(
                grade__in=['not_graded', 'unsatisfactory'])
        elif self.request.user.is_curator:
            enrollment_queryset = enrollment_queryset.annotate(
                classes_total=Count('course_offering__courseclass'))
        co_queryset = (CourseOffering.objects
                       .in_city(self.request.city_code)
                       .select_related('semester', 'course'))
        prefetch_list = [
            Prefetch('teaching_set', queryset=co_queryset.all()),
            Prefetch('shadcourserecord_set',
                     queryset=(SHADCourseRecord
                               .objects
                               .select_related("semester"))),
            Prefetch('enrollment_set', queryset=enrollment_queryset)
        ]
        select_list = []
        if self.request.user.is_curator:
            prefetch_list += ['borrows',
                              'borrows__stock',
                              'borrows__stock__book',
                              'onlinecourserecord_set',
                              'areas_of_study',
                              'cscuserreference_set']
        return (auth.get_user_model()._default_manager
                .all()
                .select_related(*select_list)
                .prefetch_related(*prefetch_list))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        u = self.request.user
        profile_user = context[self.context_object_name]
        # On Center site show club students to teachers and curators only
        if settings.SITE_ID == settings.CENTER_SITE_ID:
            if (profile_user.get_cached_groups() == {CSCUser.group.STUDENT_CLUB}
                    and not (u.is_teacher or u.is_curator)):
                raise Http404

        context['is_editing_allowed'] = (u == profile_user or u.is_curator)
        context['student_projects'] = profile_user.projects_qs()
        context['current_semester'] = Semester.get_current()
        # Assignments sorted by course name
        assignments_qs = (StudentAssignment.objects
                          .for_user(profile_user)
                          .in_term(context['current_semester']))
        context['assignments'] = u.is_curator and assignments_qs.all()
        # Initial data for photo cropper
        photo_data = {}
        if context['is_editing_allowed']:
            photo_data = {
                "user_id": profile_user.pk,
                "photo": profile_user.photo_data
            }
        context["initial"] = json.dumps(photo_data)
        # Collect stats about successfully passed courses
        if u.is_curator:
            context['stats'] = profile_user.stats(context['current_semester'])
        syllabus = None
        if profile_user.curriculum_year:
            syllabus = (StudyProgram.objects
                        .syllabus()
                        .filter(year=profile_user.curriculum_year,
                                city_id=profile_user.city_id))
        context['syllabus'] = syllabus
        return context


class UserUpdateView(ProtectedFormMixin, generic.UpdateView):
    model = CSCUser
    template_name = "users/user_edit.html"
    form_class = UserProfileForm

    def is_form_allowed(self, user, obj):
        return obj.pk == user.pk or user.is_curator


class UserReferenceCreateView(ProtectedFormMixin, generic.CreateView):
    model = CSCUserReference
    template_name = "users/reference_add.html"
    form_class = CSCUserReferenceCreateForm

    def get_initial(self):
        initial = super(UserReferenceCreateView, self).get_initial()
        initial['signature'] = self.request.user.get_full_name()
        return initial

    def form_valid(self, form):
        form.instance.student_id = self.kwargs['pk']
        return super(UserReferenceCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('user_reference_detail',
                       args=[self.object.student_id, self.object.pk])

    def is_form_allowed(self, user, obj):
        return user.is_curator


class UserReferenceDetailView(CuratorOnlyMixin, generic.DetailView):
    model = CSCUserReference
    template_name = "users/reference_detail.html"

    def get_context_data(self, *args, **kwargs):
        context = (super(UserReferenceDetailView, self)
                   .get_context_data(*args, **kwargs))
        student_info = (CSCUser.objects
                        .students_info(exclude_grades=[
                            GRADES.unsatisfactory, GRADES.not_graded
                        ])
                        .get(pk=self.object.student.pk))
        enrollments = OrderedDict()
        # From duplicated enrollments get one with higher grade
        for e in student_info.enrollments:
            if e.created > self.object.created:
                continue
            course_id = e.course_offering.course_id
            if course_id in enrollments:
                if e.grade > enrollments[course_id].grade:
                    enrollments[course_id] = e
            else:
                enrollments[course_id] = e
        context['user_enrollments'] = enrollments
        context['shads'] = filter(lambda x: x.created < self.object.created,
                                  student_info.shads)

        return context
