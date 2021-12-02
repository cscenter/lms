
import json
import os
from collections import OrderedDict
from typing import Any

from rest_framework import serializers, status
from rest_framework.response import Response

from django.apps import apps
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Prefetch, prefetch_related_objects
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from api.views import APIBaseView
from auth.mixins import PermissionRequiredMixin, RolePermissionRequiredMixin
from auth.models import ConnectedAuthService
from auth.services import get_available_service_providers, get_connected_accounts
from core.http import AuthenticatedHttpRequest
from core.timezone.utils import get_gmt
from core.urls import reverse
from core.views import ProtectedFormMixin
from courses.models import Course, CourseTeacher, Semester
from files.handlers import MemoryImageUploadHandler, TemporaryImageUploadHandler
from learning.forms import TestimonialForm
from learning.models import Enrollment, StudentAssignment
from learning.settings import GradeTypes
from study_programs.models import StudyProgram
from users.compat import get_graduate_profile as get_graduate_profile_compat
from users.models import SHADCourseRecord
from users.thumbnails import CropboxData, get_user_thumbnail, photo_thumbnail_cropbox

from .forms import CertificateOfParticipationCreateForm, UserProfileForm
from .models import CertificateOfParticipation, User
from .permissions import (
    CreateCertificateOfParticipation, ViewAccountConnectedServiceProvider,
    ViewCertificateOfParticipation
)
from .services import (
    get_graduate_profile, get_student_profile, get_student_status_history
)


class UserDetailView(LoginRequiredMixin, generic.DetailView):
    template_name = "lms/user_profile/user_detail.html"
    context_object_name = 'profile_user'

    def get_queryset(self, *args, **kwargs):
        enrollments_queryset = (Enrollment.active
                                .select_related('course',
                                                'course__main_branch',
                                                'course__semester',
                                                'course__meta_course',)
                                .order_by("course"))
        shad_courses_queryset = (SHADCourseRecord.objects
                                 .select_related("semester"))
        if not self.request.user.is_authenticated:
            enrollments_queryset = enrollments_queryset.exclude(
                grade__in=[Enrollment.GRADES.NOT_GRADED,
                           Enrollment.GRADES.UNSATISFACTORY])
            shad_courses_queryset = shad_courses_queryset.exclude(
                grade__in=[Enrollment.GRADES.NOT_GRADED,
                           Enrollment.GRADES.UNSATISFACTORY])
        elif self.request.user.is_curator:
            enrollments_queryset = enrollments_queryset.annotate(
                classes_total=Count('course__courseclass'))
        only_public_role = ~CourseTeacher.has_any_hidden_role(lookup='course_teachers__roles')
        co_queryset = (Course.objects
                       .available_on_site(self.request.site)
                       .filter(only_public_role)
                       .select_related('semester', 'meta_course',
                                       'main_branch'))
        # Limit results on compsciclub.ru
        if hasattr(self.request, "branch"):
            co_queryset = co_queryset.filter(main_branch=self.request.branch)
        prefetch_list = [
            Prefetch('teaching_set', queryset=co_queryset.all()),
            Prefetch('shadcourserecord_set', queryset=shad_courses_queryset),
            Prefetch('enrollment_set', queryset=enrollments_queryset)
        ]
        select_list = []
        if self.request.user.is_curator:
            prefetch_list += ['onlinecourserecord_set']
        filters = {}
        if not self.request.user.is_curator:
            filters["is_active"] = True
            filters["group__site_id"] = settings.SITE_ID
        return (auth.get_user_model()._default_manager
                .filter(**filters)
                .select_related(*select_list)
                .prefetch_related(*prefetch_list)
                .distinct('pk'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        u = self.request.user
        profile_user = context[self.context_object_name]
        tz = profile_user.time_zone
        context['time_zone'] = f"{get_gmt(tz)} {tz.zone}"
        icalendars = []
        if profile_user.pk == u.pk:
            ics_url_classes = reverse('user_ical_classes',
                                      subdomain=settings.LMS_SUBDOMAIN,
                                      args=[u.pk])
            ics_url_assignments = reverse('user_ical_assignments',
                                          subdomain=settings.LMS_SUBDOMAIN,
                                          args=[u.pk])
            ics_url_events = reverse('ical_events',
                                     subdomain=settings.LMS_SUBDOMAIN)
            abs_uri = self.request.build_absolute_uri
            icalendars = [
                (_("Classes"), abs_uri(ics_url_classes)),
                (_("Assignments"), abs_uri(ics_url_assignments)),
                (_("Events"), abs_uri(ics_url_events)),
            ]
        context['icalendars'] = icalendars
        is_editing_allowed = (u == profile_user or u.is_curator)
        is_library_installed = apps.is_installed("library")
        context['is_editing_allowed'] = is_editing_allowed
        context['is_certificates_of_participation_enabled'] = settings.IS_CERTIFICATES_OF_PARTICIPATION_ENABLED
        context['is_library_installed'] = is_library_installed
        context['available_providers'] = (settings.IS_SOCIAL_ACCOUNTS_ENABLED and
                                          is_editing_allowed and
                                          get_available_service_providers())
        if is_library_installed and u.is_curator:
            from library.models import Borrow
            context['borrowed_books'] = (Borrow.objects
                                         .filter(student=profile_user)
                                         .select_related('stock__book'))
        if apps.is_installed("projects"):
            from projects.services import get_student_projects
            context['student_projects'] = get_student_projects(profile_user)
        if apps.is_installed('admission'):
            context['applicant_list'] = profile_user.applicant_set.all()
        context['current_semester'] = Semester.get_current()
        # Assignments sorted by course name
        assignments_qs = (StudentAssignment.objects
                          .for_student(profile_user)
                          .in_term(context['current_semester'])
                          .order_by('assignment__course__meta_course__name',
                                    'assignment__deadline_at',
                                    'assignment__title'))
        context['assignments'] = u.is_curator and assignments_qs.all()
        js_app_data = {"props": {}}
        photo_data = {}
        if is_editing_allowed:
            photo_data = {
                "userID": profile_user.pk,
                "photo": profile_user.photo_data
            }
        js_app_data["props"]["photo"] = json.dumps(photo_data)
        js_app_data["props"]["socialAccounts"] = json.dumps({
            "isEnabled": settings.IS_SOCIAL_ACCOUNTS_ENABLED and is_editing_allowed,
            "userID": profile_user.pk,
        })
        context["appData"] = js_app_data
        # Collect stats about successfully passed courses
        if u.is_curator:
            context['stats'] = profile_user.stats(context['current_semester'])
        student_profile = get_student_profile(profile_user, self.request.site)
        syllabus = None
        graduate_profile = None
        if student_profile:
            prefetch_related_objects([student_profile],
                                     'certificates_of_participation')
            syllabus = (StudyProgram.objects
                        .select_related("academic_discipline")
                        .prefetch_core_courses_groups()
                        .filter(year=student_profile.year_of_curriculum,
                                branch_id=student_profile.branch_id))
            graduate_profile = get_graduate_profile(student_profile)
            if u.is_curator:
                context['student_status_history'] = get_student_status_history(student_profile)
        context['syllabus'] = syllabus
        context['student_profile'] = student_profile
        context['graduate_profile'] = graduate_profile
        return context


class UserUpdateView(ProtectedFormMixin, generic.UpdateView):
    model = User
    template_name = "users/user_edit.html"
    form_class = UserProfileForm

    def is_form_allowed(self, user, obj):
        return obj.pk == user.pk or user.is_curator

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        graduate_profile = get_graduate_profile_compat(self.object,
                                                       self.request.site)
        if graduate_profile:
            context["testimonial_form"] = TestimonialForm(
                instance=graduate_profile)
        return context

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        with transaction.atomic():
            self.object = form.save()
            graduate_profile = get_graduate_profile_compat(self.object,
                                                           self.request.site)
            if graduate_profile:
                testimonial_form = TestimonialForm(instance=graduate_profile,
                                                   data=self.request.POST)
                assert testimonial_form.is_valid()
                testimonial = testimonial_form.cleaned_data['testimonial']
                graduate_profile.testimonial = testimonial
                graduate_profile.save()
        return super().form_valid(form)


class ConnectedAuthServicesView(RolePermissionRequiredMixin, APIBaseView):
    permission_classes = [ViewAccountConnectedServiceProvider]
    request: AuthenticatedHttpRequest
    account: User

    class InputSerializer(serializers.Serializer):
        user = serializers.IntegerField()

    class OutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = ConnectedAuthService
            fields = ('provider', 'uid')

    def setup(self, request: AuthenticatedHttpRequest, **kwargs: Any):
        super().setup(request, **kwargs)
        serializer = self.InputSerializer(data=kwargs)
        serializer.is_valid(raise_exception=True)
        queryset = (User.objects
                    .filter(pk=serializer.validated_data['user']))
        self.account = get_object_or_404(queryset)

    def get_permission_object(self) -> User:
        return self.account

    def get(self, request: AuthenticatedHttpRequest, **kwargs) -> Response:
        connected_accounts = get_connected_accounts(user=self.account)
        data = self.OutputSerializer(connected_accounts, many=True).data
        return Response(status=status.HTTP_200_OK, data={
            "edges": data
        })


class CertificateOfParticipationCreateView(PermissionRequiredMixin,
                                           generic.CreateView):
    model = CertificateOfParticipation
    template_name = "users/reference_add.html"
    form_class = CertificateOfParticipationCreateForm
    permission_required = CreateCertificateOfParticipation.name

    def get_initial(self):
        initial = super().get_initial()
        initial['signature'] = self.request.user.get_full_name()
        return initial

    def form_valid(self, form):
        form.instance.student_profile_id = self.kwargs['student_profile_id']
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()


class CertificateOfParticipationDetailView(PermissionRequiredMixin,
                                           generic.DetailView):
    pk_url_kwarg = 'reference_pk'
    template_name = "users/reference_detail.html"
    permission_required = ViewCertificateOfParticipation.name

    def get_queryset(self):
        return (CertificateOfParticipation.objects
                .filter(student_profile_id=self.kwargs['student_profile_id'])
                .select_related('student_profile'))

    def get_context_data(self, **kwargs):
        from learning.reports import ProgressReport
        student_info = (User.objects
                        .student_progress(exclude_grades=GradeTypes.unsatisfactory_grades)
                        .get(pk=self.object.student_profile.user_id))
        courses_qs = (ProgressReport().get_courses_queryset((student_info,)))
        courses = {c.pk: c for c in courses_qs}
        for e in student_info.enrollments_progress:
            e.course = courses[e.course_id]
        enrollments = OrderedDict()
        # Among enrollments for the same course get the latest one
        student_info.enrollments_progress.sort(key=lambda e: e.course.meta_course.name)
        for e in student_info.enrollments_progress:
            if e.created > self.object.created:
                continue
            enrollments[e.course.meta_course_id] = e
        context = {
            'certificate_of_participation': self.object,
            'user_enrollments': enrollments,
            'shads': filter(lambda x: x.created < self.object.created,
                            student_info.shads)
        }
        return context


class ProfileImageUpdate(generic.base.View):
    """
    This view saves new profile image or updates preview dimensions
    (cropbox data) for the already uploaded image.
    """
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """
        Upload handlers will be triggered by accessing `request.POST` or
        `request.FILES`. `CsrfViewMiddleware` internally use `request.POST`
        but only if protection is enabled. So workaround is:
            * delay CSRF protection using `csrf_exempt` decorator
            * modify upload handlers of the request object
            * enable CSRF-protection for the view with `csrf_protect` decorator
        """
        request.upload_handlers = [MemoryImageUploadHandler(request),
                                   TemporaryImageUploadHandler(request)]
        return self._dispatch(request, *args, **kwargs)

    @method_decorator(csrf_protect)
    def _dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseBadRequest("Bad User")

        user_id = kwargs['pk']
        if user_id != request.user.id and not request.user.is_curator:
            return HttpResponseForbidden()

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return HttpResponseBadRequest("User not found")

        if "crop_data" in request.POST:
            return self._update_cropbox(request, user)
        else:
            return self._update_image(request, user)

    @staticmethod
    def _update_cropbox(request, user):
        crop_data_form = CropboxData(data=request.POST)
        if not crop_data_form.is_valid():
            return JsonResponse({
                "success": False,
                "reason": "Invalid cropbox data"
            })
        crop_data_str = photo_thumbnail_cropbox(crop_data_form.to_json())
        thumbnail = get_user_thumbnail(user, User.ThumbnailSize.BASE,
                                       crop='center', use_stub=False,
                                       cropbox=crop_data_str)
        if thumbnail:
            user.cropbox_data = crop_data_form.to_json()
            user.save(update_fields=['cropbox_data'])
            ret_json = {"success": True, "thumbnail": thumbnail.url}
        else:
            ret_json = {"success": False, "reason": "Thumbnail generation error"}
        return JsonResponse(ret_json)

    def _update_image(self, request, user):
        if len(request.FILES) > 1:
            return HttpResponseBadRequest("Multi upload is not supported")
        elif len(request.FILES) != 1:
            return HttpResponseBadRequest("Bad file format or size")

        image_file = list(request.FILES.values())[0]
        user.photo = image_file
        user.cropbox_data = {}
        user.save(update_fields=['photo', 'cropbox_data'])
        image_url = user.photo.url

        # TODO: generate default crop settings and return them
        payload = {
            'success': True,
            "url": image_url,
            'filename': os.path.basename(user.photo.name)
        }
        return JsonResponse(payload)
