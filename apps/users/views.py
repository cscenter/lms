# -*- coding: utf-8 -*-

import json
import os
from collections import OrderedDict

from django.apps import apps
from django.conf import settings
from django.contrib import auth
from django.db import transaction
from django.db.models import Prefetch, Count
from django.http import HttpResponseBadRequest, \
    JsonResponse
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.csrf import csrf_exempt, csrf_protect

from ajaxuploader.backends import ProfileImageUploadBackend
from ajaxuploader.handlers import MemoryImageUploadHandler, \
    TemporaryImageUploadHandler
from ajaxuploader.signals import file_uploaded
from auth.mixins import PermissionRequiredMixin
from core.views import ProtectedFormMixin
from courses.models import Course, Semester
from learning.forms import TestimonialForm
from learning.models import StudentAssignment, \
    Enrollment
from learning.services import get_student_profile
from learning.settings import GradeTypes
from study_programs.models import StudyProgram
from users.models import SHADCourseRecord
from users.thumbnails import get_user_thumbnail, photo_thumbnail_cropbox
from .forms import UserProfileForm, EnrollmentCertificateCreateForm
from .models import User, EnrollmentCertificate
from .permissions import CreateCertificateOfParticipation, \
    ViewCertificateOfParticipation


class UserDetailView(generic.DetailView):
    template_name = "users/user_detail.html"
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
        co_queryset = Course.objects.select_related('semester',
                                                    'meta_course',
                                                    'main_branch')
        if hasattr(self.request, "branch"):
            co_queryset = co_queryset.filter(main_branch=self.request.branch)
        prefetch_list = [
            Prefetch('teaching_set', queryset=co_queryset.all()),
            Prefetch('shadcourserecord_set', queryset=shad_courses_queryset),
            Prefetch('enrollment_set', queryset=enrollments_queryset)
        ]
        select_list = []
        if self.request.user.is_curator:
            select_list += ['graduate_profile']
            prefetch_list += ['borrows',
                              'borrows__stock',
                              'borrows__stock__book',
                              'onlinecourserecord_set',
                              'enrollment_certificates']
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
        context['is_editing_allowed'] = (u == profile_user or u.is_curator)
        if apps.is_installed("projects"):
            from projects.models import ProjectStudent
            context['student_projects'] = (ProjectStudent.objects
                                           .filter(student_id=profile_user.pk)
                                           .select_related('project',
                                                           'project__semester')
                                           .order_by('project__semester__index'))
        context['current_semester'] = Semester.get_current()
        # Assignments sorted by course name
        assignments_qs = (StudentAssignment.objects
                          .for_user(profile_user)
                          .in_term(context['current_semester'])
                          .order_by('assignment__course__meta_course__name',
                                    'assignment__deadline_at',
                                    'assignment__title'))
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
        student_profile = get_student_profile(profile_user, self.request.site)
        syllabus = None
        if student_profile:
            syllabus = (StudyProgram.objects
                        .select_related("academic_discipline")
                        .prefetch_core_courses_groups()
                        .filter(year=student_profile.year_of_curriculum,
                                branch_id=student_profile.branch_id))
        context['syllabus'] = syllabus
        context['student_profile'] = student_profile
        return context


class UserUpdateView(ProtectedFormMixin, generic.UpdateView):
    model = User
    template_name = "users/user_edit.html"
    form_class = UserProfileForm

    def is_form_allowed(self, user, obj):
        return obj.pk == user.pk or user.is_curator

    def get_queryset(self):
        return super().get_queryset().select_related("graduate_profile")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self.object, "graduate_profile"):
            profile = self.object.graduate_profile
            context["testimonial_form"] = TestimonialForm(instance=profile)
        return context

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        with transaction.atomic():
            self.object = form.save()
            if hasattr(self.object, "graduate_profile"):
                profile = self.object.graduate_profile
                testimonial_form = TestimonialForm(instance=profile,
                                                   data=self.request.POST)
                # This one always should be valid
                assert testimonial_form.is_valid()
                profile.testimonial = testimonial_form.cleaned_data['testimonial']
                profile.save()
        return super().form_valid(form)


class CertificateOfParticipationCreateView(PermissionRequiredMixin,
                                           generic.CreateView):
    model = EnrollmentCertificate
    template_name = "users/reference_add.html"
    form_class = EnrollmentCertificateCreateForm
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
        return (EnrollmentCertificate.objects
                .filter(student_profile_id=self.kwargs['student_profile_id'])
                .select_related('student_profile'))

    def get_context_data(self, **kwargs):
        from learning.reports import ProgressReport
        student_info = (User.objects
                        .student_progress(exclude_grades=[
                            GradeTypes.UNSATISFACTORY, GradeTypes.NOT_GRADED
                        ])
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
    This view validates mime type on uploading file.
    """
    backend = ProfileImageUploadBackend

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """
        Modifying upload handlers before accessing `request.POST` or
        `request.FILES`.

        It doesn’t make sense to change upload handlers after upload handling
        has already started. Since `request.POST` is accessed by
        CsrfViewMiddleware, use `csrf_exempt` decorator to allow to
        change the upload handlers and `csrf_protect` on further view function
        to enable CSRF-protection.
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
        if not request.user.is_curator and user_id != request.user.id:
            return HttpResponseBadRequest("Bad User")

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return HttpResponseBadRequest("Bad User")

        if "crop_data" in request.POST:
            return self._update_cropbox(request, user)
        else:
            return self._update_image(request, user)

    @staticmethod
    def _update_cropbox(request, user):
        # TODO: add validation for unbound coords and width=img.width
        attrs = ("width", "height", "x", "y")
        try:
            data = {attr: int(float(request.POST.get(attr))) for attr in attrs}
        except (KeyError, ValueError):
            return False

        thumbnail = get_user_thumbnail(user, User.ThumbnailSize.BASE,
                                       crop='center', use_stub=False,
                                       cropbox=photo_thumbnail_cropbox(data))
        if not thumbnail:
            ret_json = {"success": False, "reason": "Thumbnail generation error"}
        else:
            user.cropbox_data = data
            user.save(update_fields=['cropbox_data'])
            ret_json = {"success": True, "thumbnail": thumbnail.url}
        return JsonResponse(ret_json)

    def _update_image(self, request, user):
        if len(request.FILES) > 1:
            return HttpResponseBadRequest("Multi upload is not supported")

        if len(request.FILES) == 1:
            upload = list(request.FILES.values())[0]
        else:
            return HttpResponseBadRequest("Bad file format or size")

        try:
            _, file_ext = os.path.splitext(request.POST['_photo'])
            filename = f"{user.id}{file_ext}"
        except KeyError:
            return HttpResponseBadRequest("Photo not found")

        backend = self.backend()
        # custom filename handler
        filename = (backend.update_filename(request, filename) or filename)
        backend.setup(filename)  # save empty file
        success = backend.upload(upload, filename, False)

        if success:
            user.photo.name = filename
            user.cropbox_data = {}
            user.save()
            # Send signals
            file_uploaded.send(sender=self.__class__, backend=backend,
                               request=request)

        extra_context = backend.upload_complete(request, filename)

        # TODO: generate default crop settings and return them
        ret_json = {'success': success, 'filename': filename}
        if extra_context is not None:
            ret_json.update(extra_context)

        return JsonResponse(ret_json)
