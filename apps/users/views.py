# -*- coding: utf-8 -*-

import json
import os
from collections import OrderedDict

from django.conf import settings
from django.contrib import auth
from django.db import transaction
from django.db.models import Prefetch, Count
from django.http import Http404, HttpResponseBadRequest, \
    JsonResponse
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from vanilla import DetailView

from ajaxuploader.backends import ProfileImageUploadBackend
from ajaxuploader.handlers import MemoryImageUploadHandler, \
    TemporaryImageUploadHandler
from ajaxuploader.signals import file_uploaded
from core.utils import is_club_site
from core.views import ProtectedFormMixin
from courses.models import Course, Semester
from learning.forms import TestimonialForm
from learning.models import StudentAssignment, \
    Enrollment
from learning.settings import GradeTypes
from study_programs.models import StudyProgram
from users.constants import AcademicRoles
from users.mixins import CuratorOnlyMixin
from users.models import SHADCourseRecord
from users.thumbnails import get_user_thumbnail, photo_thumbnail_cropbox
from .forms import UserProfileForm, EnrollmentCertificateCreateForm
from .models import User, EnrollmentCertificate


class TeacherDetailView(DetailView):
    template_name = "users/teacher_detail.html"
    context_object_name = 'teacher'

    def get_queryset(self, *args, **kwargs):
        filters = {"city_code": settings.CENTER_BRANCHES_CITY_CODES}
        if is_club_site():
            filters["city_code"] = self.request.city_code
        co_queryset = (Course.objects
                       .in_city(**filters)
                       .select_related('semester', 'meta_course'))
        return (User.objects
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
        enrollments_queryset = Enrollment.active.select_related(
            'course',
            'course__semester',
            'course__meta_course'
        )
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
        filters = {"city_code": settings.CENTER_BRANCHES_CITY_CODES}
        if is_club_site():
            filters["city_code"] = self.request.city_code
        co_queryset = (Course.objects
                       .in_city(**filters)
                       .select_related('semester', 'meta_course'))
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
        context['student_projects'] = profile_user.get_projects_queryset()
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
                        .select_related("academic_discipline")
                        .prefetch_core_courses_groups()
                        .filter(year=profile_user.curriculum_year,
                                city_id=profile_user.city_id))
        context['syllabus'] = syllabus
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


class EnrollmentCertificateCreateView(ProtectedFormMixin, generic.CreateView):
    model = EnrollmentCertificate
    template_name = "users/reference_add.html"
    form_class = EnrollmentCertificateCreateForm

    def get_initial(self):
        initial = super(EnrollmentCertificateCreateView, self).get_initial()
        initial['signature'] = self.request.user.get_full_name()
        return initial

    def form_valid(self, form):
        form.instance.student_id = self.kwargs['pk']
        return super(EnrollmentCertificateCreateView, self).form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()

    def is_form_allowed(self, user, obj):
        return user.is_curator


class EnrollmentCertificateDetailView(CuratorOnlyMixin, generic.DetailView):
    model = EnrollmentCertificate
    pk_url_kwarg = 'reference_pk'
    template_name = "users/reference_detail.html"

    def get_context_data(self, **kwargs):
        student_info = (User.objects
                        .has_role(AcademicRoles.STUDENT,
                                  AcademicRoles.GRADUATE,
                                  AcademicRoles.VOLUNTEER)
                        .students_info(exclude_grades=[
                            GradeTypes.UNSATISFACTORY, GradeTypes.NOT_GRADED
                        ])
                        .get(pk=self.object.student.pk))
        enrollments = OrderedDict()
        # Among enrollments for the same course get one with the highest grade
        for e in student_info.enrollments:
            if e.created > self.object.created:
                continue
            meta_course_id = e.course.meta_course_id
            if meta_course_id in enrollments:
                if e.grade > enrollments[meta_course_id].grade:
                    enrollments[meta_course_id] = e
            else:
                enrollments[meta_course_id] = e
        context = {
            'object': self.object,
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
