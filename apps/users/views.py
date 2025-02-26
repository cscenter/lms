
import json
import os
from collections import OrderedDict
from typing import Any, Optional

from django.utils.datetime_safe import datetime
from django.utils.timezone import now
from rest_framework import serializers, status
from rest_framework.response import Response

from django.apps import apps
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from api.views import APIBaseView
from apps.courses.utils import date_to_term_pair
from auth.mixins import PermissionRequiredMixin, RolePermissionRequiredMixin
from auth.models import ConnectedAuthService
from auth.services import get_available_service_providers, get_connected_accounts
from core.http import AuthenticatedHttpRequest, HttpRequest
from core.timezone.utils import get_gmt
from core.urls import reverse
from core.views import ProtectedFormMixin
from courses.models import CourseTeacher, Semester, CourseDurations
from courses.selectors import get_site_courses
from files.handlers import MemoryImageUploadHandler, TemporaryImageUploadHandler
from learning.forms import TestimonialForm
from learning.icalendar import get_icalendar_links
from learning.models import Enrollment, StudentAssignment
from learning.settings import GradeTypes, StudentStatuses, EnrollmentTypes
from users.compat import get_graduate_profile as get_graduate_profile_compat
from users.models import SHADCourseRecord, YandexUserData, StudentTypes
from users.thumbnails import CropboxData, get_user_thumbnail, photo_thumbnail_cropbox

from .forms import CertificateOfParticipationCreateForm, UserProfileForm
from .models import CertificateOfParticipation, User
from .permissions import (
    CreateCertificateOfParticipation, ViewAccountConnectedServiceProvider,
    ViewCertificateOfParticipation
)
from .services import get_student_profile, get_student_profiles


class UserDetailView(LoginRequiredMixin, generic.TemplateView):
    template_name = "lms/user_profile/user_detail.html"

    def get_queryset(self, *args, **kwargs):
        enrollments_queryset = (Enrollment.active
                                .select_related('course',
                                                'course__main_branch',
                                                'course__semester',
                                                'course__meta_course',
                                                'course__main_branch__site__site_configuration')
                                .order_by("course"))
        shad_courses_queryset = (SHADCourseRecord.objects
                                 .select_related("semester"))
        # Construct queryset for courses available on the site
        only_public_role = ~CourseTeacher.has_any_hidden_role(lookup='course_teachers__roles')
        filters = [only_public_role]
        # Limit results on compsciclub.ru
        if hasattr(self.request, "branch"):
            filters.append(Q(main_branch=self.request.branch))
        site_courses_queryset = get_site_courses(site=self.request.site, filters=filters)
        prefetch_list = [
            Prefetch('teaching_set', queryset=site_courses_queryset),
            Prefetch('shadcourserecord_set', queryset=shad_courses_queryset),
            Prefetch('enrollment_set', queryset=enrollments_queryset)
        ]
        if self.request.user.is_curator:
            prefetch_list += ['onlinecourserecord_set']
        filters = {}
        if not self.request.user.is_curator:
            filters["is_active"] = True
            filters["group__site_id"] = settings.SITE_ID
        return (auth.get_user_model()._default_manager
                .filter(**filters)
                .prefetch_related(*prefetch_list)
                .distinct('pk'))

    def get_context_data(self, **kwargs):
        u = self.request.user
        profile_user = get_object_or_404(
            self.get_queryset()
                .filter(pk=kwargs['pk'])
                .select_related('yandex_data')
        )
        is_library_installed = apps.is_installed("library")
        is_certificates_of_participation_enabled = settings.IS_CERTIFICATES_OF_PARTICIPATION_ENABLED
        is_social_accounts_enabled = settings.IS_SOCIAL_ACCOUNTS_ENABLED
        can_edit_profile = (u == profile_user or u.is_curator)
        can_view_student_profiles = (u == profile_user or u.is_curator)
        can_view_assignments = u.is_curator
        can_view_course_icons = u.is_curator
        can_view_library = is_library_installed and u.is_curator
        icalendars = []
        if profile_user.pk == u.pk:
            icalendars = get_icalendar_links(profile_user)
        current_semester = Semester.get_current()
        context = {
            "StudentStatuses": StudentStatuses,
            'StudentTypes': StudentTypes,
            "CourseDurations": CourseDurations,
            "profile_user": profile_user,
            "time_zone": f"{get_gmt(profile_user.time_zone)} {profile_user.time_zone.zone}",
            "icalendars": icalendars,
            "is_certificates_of_participation_enabled": is_certificates_of_participation_enabled,
            "can_edit_profile": can_edit_profile,
            "can_view_library": can_view_library,
            "current_semester": current_semester,
            "can_view_student_profiles": can_view_student_profiles,
            "can_view_assignments": can_view_assignments,
            "can_view_course_icons": can_view_course_icons,
            "yandex_oauth_url": reverse('auth:users:yandex_begin'),
            "is_yds_site": self.request.site.pk == settings.YDS_SITE_ID
        }
        enrollments = profile_user.enrollment_set.all().select_related("student_profile")
        for enrollment in enrollments:
            enrollment.satisfactory = enrollment.grade in GradeTypes.satisfactory_grades or \
                        (enrollment.grade == GradeTypes.NOT_GRADED and enrollment.course.semester == current_semester)
            enrollment.view_invited = enrollment.student_profile.type == StudentTypes.INVITED
            enrollment.view_partner = enrollment.student_profile.type == StudentTypes.PARTNER
            enrollment.view_lections_only = enrollment.type == EnrollmentTypes.LECTIONS_ONLY
        context["enrollments"] = enrollments
        if is_certificates_of_participation_enabled:
            certificates = (CertificateOfParticipation.objects
                            .filter(student_profile__user=profile_user)
                            .order_by('student_profile__pk'))
            context['certificates_of_participation'] = certificates
        context['available_providers'] = (is_social_accounts_enabled and
                                          can_edit_profile and
                                          get_available_service_providers())
        if is_library_installed and can_view_library:
            from library.models import Borrow
            context['borrowed_books'] = (Borrow.objects
                                         .filter(student=profile_user)
                                         .select_related('stock__book'))
        if apps.is_installed("projects"):
            from projects.services import get_student_projects
            context['student_projects'] = get_student_projects(profile_user)
        if apps.is_installed('admission'):
            context['applicant_list'] = profile_user.applicant_set.all()
        if can_view_assignments:
            assignments_qs = (StudentAssignment.objects
                              .for_student(profile_user)
                              .in_term(current_semester)
                              .active()
                              .order_by('assignment__course__meta_course__name',
                                        'assignment__deadline_at',
                                        'assignment__title'))
            context['personal_assignments'] = assignments_qs.all()
        js_app_data = {"props": {}}
        photo_data = {}
        if can_edit_profile:
            photo_data = {
                "userID": profile_user.pk,
                "photo": profile_user.photo_data
            }
        js_app_data["props"]["photo"] = json.dumps(photo_data)
        js_app_data["props"]["socialAccounts"] = json.dumps({
            "isEnabled": is_social_accounts_enabled and can_edit_profile,
            "userID": profile_user.pk,
        })
        context["appData"] = js_app_data
        # Collect stats about successfully passed courses
        if u.is_curator:
            # TODO: add derivable classes_total field to Course model
            queryset = (profile_user.enrollment_set(manager='active')
                        .annotate(classes_total=Count('course__courseclass')))
            context['stats'] = profile_user.stats(current_semester,
                                                  enrollments=queryset)
        if can_view_student_profiles:
            student_profiles = get_student_profiles(user=profile_user,
                                                    site=self.request.site,
                                                    fetch_graduate_profile=True,
                                                    fetch_status_history=True,
                                                    fetch_invitation=True,
                                                    fetch_academic_disciplines=True)
            # Aggregate stats needed for student profiles
            passed_courses = set()
            in_current_term = set()
            for enrollment in profile_user.enrollment_set.all():
                if enrollment.grade in GradeTypes.satisfactory_grades:
                    passed_courses.add(enrollment.course.meta_course_id)
                if enrollment.course.semester_id == current_semester.pk:
                    in_current_term.add(enrollment.course.meta_course_id)
            context['student_profiles'] = student_profiles
            context['syllabus_legend'] = {
                'passed_courses': passed_courses,
                'in_current_term': in_current_term
            }
            if student_profiles:
                main_profile = student_profiles[0]  # because of profile ordering
                context['academic_disciplines'] = ", ".join(d.name for d in main_profile.academic_disciplines.all())
                actual_student_profile = next((profile for profile in student_profiles if profile.type is not StudentTypes.INVITED), None)
                if actual_student_profile:
                    context['student_actual_status'] = actual_student_profile.status if actual_student_profile.status else _("Studying")
                    context['student_actual_academic_discipline'] = actual_student_profile.academic_discipline
                    context['student_actual_year_of_curriculum'] = actual_student_profile.year_of_curriculum
        return context


class UserUpdateView(ProtectedFormMixin, generic.UpdateView):
    model = User
    template_name = "lms/user_profile/user_edit.html"
    form_class = UserProfileForm

    def get_form_kwargs(self):
        kwargs = super(UserUpdateView, self).get_form_kwargs()
        kwargs.update({'editor': self.request.user,
                       'student': self.object,
                       'initial': {'yandex_login': self.object.get_yandex_login()}})
        return kwargs

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
        yandex_login = form.cleaned_data['yandex_login']
        if yandex_login and self.request.user.is_curator:
            (YandexUserData.objects
             .filter(user=self.object)
             .exclude(login=yandex_login)
             .update(login=yandex_login,
                     changed_by=self.request.user,
                     modified_at=now()))
        return super().form_valid(form)


class ConnectedAuthServicesView(RolePermissionRequiredMixin, APIBaseView):
    permission_classes = [ViewAccountConnectedServiceProvider]
    request: AuthenticatedHttpRequest
    account: User

    class InputSerializer(serializers.Serializer):
        user = serializers.IntegerField()

    class OutputSerializer(serializers.ModelSerializer):
        login = serializers.SerializerMethodField()

        class Meta:
            model = ConnectedAuthService
            fields = ('provider', 'uid', 'login')

        def get_login(self, obj: ConnectedAuthService) -> Optional[str]:
            return obj.login

    def setup(self, request: HttpRequest, **kwargs: Any) -> None:
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

    def form_valid(self, form):
        user = get_object_or_404(User.objects.filter(pk=self.kwargs['user_id']))
        student_profile = get_student_profile(user=user, site=self.request.site, profile_type=StudentTypes.REGULAR)
        if student_profile is None:
            messages.error(self.request, "Профиль обычного студента не найден.")
            return redirect(self.get_success_url())
        form.instance.student_profile_id = student_profile.pk
        return super().form_valid(form)

    def get_success_url(self):
        user = get_object_or_404(User.objects.filter(pk=self.kwargs['user_id']))
        return f"{user.get_absolute_url()}#for-curator-tab"


class CertificateOfParticipationDetailView(PermissionRequiredMixin,
                                           generic.DetailView):
    pk_url_kwarg = 'reference_pk'
    template_name = "users/reference_csc_detail.html"
    permission_required = ViewCertificateOfParticipation.name

    ALLOWED_TEMPLATE_NAMES = [
        'csc',
        'shad_ru_with_courses',
        'shad_ru_without_courses',
        'shad_en_with_courses',
        'shad_en_without_courses'
    ]

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.student_profile.year_of_curriculum is None:
            messages.error(request, "Год программы обучения студента не выставлен")
        if self.object.student_profile.academic_discipline is None:
            messages.error(request, "Направление обучения студента не выставлено")
        return super().get(request, *args, **kwargs)

    def get_template_names(self):
        template_name = self.request.GET.get('style')
        if template_name not in self.ALLOWED_TEMPLATE_NAMES:
            template_name = self.ALLOWED_TEMPLATE_NAMES[0]
        return [f"users/reference_{template_name}_detail.html"]

    def get_queryset(self):
        return (CertificateOfParticipation.objects
                .filter(student_profile__user_id=self.kwargs['user_id'])
                .select_related('student_profile'))
        
    def filter_enrollments(self, enrollments):
        # Only courses within study period of regular student profile must be included
        start_term_pair = date_to_term_pair(datetime(day=1, month=9, year=self.object.student_profile.year_of_admission,
                                           tzinfo=self.object.student_profile.branch.time_zone))
        start_semester = Semester.objects.get(year=start_term_pair.year,
                                                 type=start_term_pair.type)
        enrolments_period_end = self.object.created
        if self.object.student_profile.year_of_curriculum is not None:
            enrolments_period_end = min(datetime(day=30, month=5, year=self.object.student_profile.year_of_curriculum + 2,
                         tzinfo=self.object.student_profile.branch.time_zone), enrolments_period_end)
        end_term_pair = date_to_term_pair(enrolments_period_end)
        end_semester = Semester.objects.get(year=end_term_pair.year,
                                                 type=end_term_pair.type)
        return [enrollment for enrollment in enrollments if start_semester <= enrollment.course.semester <= end_semester]

    def get_context_data(self, **kwargs):
        from learning.reports import ProgressReport
        student_info = (User.objects
                        .student_progress(exclude_grades=[*GradeTypes.unsatisfactory_grades, GradeTypes.RE_CREDIT],
                                          exclude_invisible_courses=True)
                        .get(pk=self.object.student_profile.user_id))
        courses_qs = (ProgressReport().get_courses_queryset((student_info,)))
        courses = {c.pk: c for c in courses_qs}
        for e in student_info.enrollments_progress:
            e.course = courses[e.course_id]
        enrollments = OrderedDict()
        # Among enrollments for the same course get the latest one
        student_info.enrollments_progress.sort(key=lambda e: (e.course.semester, e.course.meta_course.name))
        for e in self.filter_enrollments(student_info.enrollments_progress):
            enrollments[e.course.meta_course_id] = e
        context = {
            'certificate_of_participation': self.object,
            'enrollments': list(enrollments.values())
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
