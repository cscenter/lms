import csv
import itertools
from typing import Any, Optional

from rest_framework import serializers, status
from rest_framework.response import Response

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.translation import gettext_lazy as _
from django.views import View, generic
from django.views.generic.base import TemplateResponseMixin

from api.views import APIBaseView
from auth.mixins import PermissionRequiredMixin, RolePermissionRequiredMixin
from auth.models import ConnectedAuthService
from core.http import AuthenticatedHttpRequest, HttpRequest
from core.utils import bucketize, normalize_yandex_login
from courses.constants import AssignmentFormat, SemesterTypes
from courses.models import Assignment, Course, Semester
from courses.utils import get_current_term_pair
from courses.views.mixins import CourseURLParamsMixin
from grading.api.yandex_contest import (
    ContestAPIError, Unavailable, YandexContestAPI, cast_contest_error
)
from learning.gradebook import (
    BaseGradebookForm, GradeBookFilterForm, GradeBookFormFactory, gradebook_data
)
from learning.gradebook.services import (
    assignment_import_scores_from_csv, assignment_import_scores_from_yandex_contest,
    get_assignment_checker, get_course_students, get_course_students_by_stepik_id,
    get_course_students_by_yandex_login
)
from learning.models import StudentGroup
from learning.permissions import EditGradebook, ViewGradebook

__all__ = [
    "GradeBookView",
    "GradeBookCSVView", "ImportAssignmentScoresByStepikIDView",
    "ImportAssignmentScoresByYandexLoginView"
]

from users.models import StudentTypes, User


class GradeBookListBaseView(generic.ListView):
    model = Semester

    def get_course_queryset(self):
        return (Course.objects
                .available_on_site(self.request.site)
                .select_related("meta_course", "main_branch")
                .order_by("meta_course__name"))

    def get_term_threshold(self):
        tz = self.request.user.time_zone
        term_pair = get_current_term_pair(tz)
        term_index = term_pair.index
        # Skip to the spring semester
        if term_pair.type == SemesterTypes.AUTUMN:
            spring_order = SemesterTypes.get_choice(SemesterTypes.SPRING).order
            autumn_order = SemesterTypes.get_choice(SemesterTypes.AUTUMN).order
            # How many terms are between spring and autumn
            spring_autumn_gap = abs(autumn_order - spring_order - 1)
            term_index += spring_autumn_gap
        return term_index

    def get_queryset(self):
        return (Semester.objects
                .filter(index__lte=self.get_term_threshold())
                .exclude(type=SemesterTypes.SUMMER)
                .order_by('-index')
                .prefetch_related(
                    Prefetch(
                        "course_set",
                        queryset=self.get_course_queryset(),
                        to_attr="course_offerings"
                    )))


class GradeBookView(PermissionRequiredMixin, CourseURLParamsMixin,
                    TemplateResponseMixin, View):
    is_for_staff = False
    user_type = 'teacher'
    template_name = "lms/gradebook/gradebook_form.html"
    context_object_name = 'assignment_list'
    permission_required = ViewGradebook.name

    def get_permission_object(self):
        return self.course

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = None
        self.is_for_staff = kwargs.get('is_for_staff', False)

    def get(self, request, *args, **kwargs):
        filter_form = GradeBookFilterForm(data=request.GET, course=self.course)
        selected_group = None
        if filter_form.is_valid():
            selected_group = filter_form.cleaned_data['student_group']
        form = self.get_form(request.user, student_group=selected_group)
        context = self.get_context_data(form=form, filter_form=filter_form)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm(EditGradebook.name, self.course):
            raise PermissionDenied
        filter_form = GradeBookFilterForm(data=request.GET, course=self.course)
        selected_group = None
        if filter_form.is_valid():
            selected_group = filter_form.cleaned_data['student_group']
        form = self.get_form(request.user, data=request.POST, files=request.FILES,
                             student_group=selected_group)
        if form.is_valid():
            return self.form_valid(form, selected_group)
        return self.form_invalid(form)

    def get_form(self, user: User, data=None, files=None,
                 student_group: Optional[int] = None, **kwargs):
        self.data = gradebook_data(self.course, student_group)
        can_edit_gradebook = not user.has_perm(EditGradebook.name, self.course)
        cls = GradeBookFormFactory.build_form_class(self.data, is_readonly=can_edit_gradebook)
        # Set initial data for all GET-requests
        if not data and "initial" not in kwargs:
            initial = GradeBookFormFactory.transform_to_initial(self.data)
            kwargs["initial"] = initial
        return cls(data=data, files=files, **kwargs)

    def form_valid(self, form: BaseGradebookForm,
                   student_group: Optional[StudentGroup] = None):
        conflicts_on_save = form.save()
        if conflicts_on_save:
            msg = _("<b>Внимание, часть данных не была сохранена!</b><br>"
                    "В процессе редактирования данные были "
                    "изменены другими участниками. Необходимо вручную "
                    "разрешить конфликты и повторить отправку формы.")
            messages.warning(self.request, str(msg))
            return self._form_invalid(form)
        messages.success(self.request,
                         str(_('Gradebook successfully saved.')),
                         extra_tags='timeout')
        if self.is_for_staff:
            params = {"url_name": "staff:gradebook"}
        else:
            params = {}
        url = self.course.get_gradebook_url(student_group=student_group, **params)
        return redirect(url)

    def form_invalid(self, form: BaseGradebookForm):
        msg = _("Gradebook hasn't been saved.")
        messages.error(self.request, str(msg))
        return self._form_invalid(form)

    def _form_invalid(self, form: BaseGradebookForm):
        """
        Extends form data with the values missing in the POST request (client
        sends only changed values)
        """
        filter_form = GradeBookFilterForm(data=self.request.GET, course=self.course)
        student_group = None
        if filter_form.is_valid():
            student_group = filter_form.cleaned_data['student_group']
        self.data = gradebook_data(self.course, student_group=student_group)
        current_data = GradeBookFormFactory.transform_to_initial(self.data)
        data = form.data.copy()
        for k, v in current_data.items():
            if k not in data:
                data[k] = v
        form.data = data
        context = self.get_context_data(form=form, filter_form=filter_form)
        return self.render_to_response(context)

    def get_context_data(self, form: BaseGradebookForm,
                         filter_form: GradeBookFilterForm, **kwargs: Any):
        context = {
            'view': self,
            'form': form,
            'filter_form': filter_form,
            "StudentTypes": StudentTypes,
            "gradebook": self.data,
            'AssignmentFormat': AssignmentFormat
        }
        # TODO: Move to the model
        filter_kwargs = {}
        if not self.request.user.is_curator:
            filter_kwargs["teachers"] = self.request.user
        courses = (Course.objects
                   .filter(**filter_kwargs)
                   .order_by('-semester__index', '-pk')
                   .select_related('semester', 'meta_course', 'main_branch'))
        context['course_offering_list'] = courses
        context['user_type'] = self.user_type

        return context


class GradeBookCSVView(PermissionRequiredMixin, CourseURLParamsMixin,
                       generic.base.View):
    permission_required = ViewGradebook.name

    def get_permission_object(self):
        return self.course

    def get(self, request, *args, **kwargs):
        gradebook = gradebook_data(self.course)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = "{}-{}-{}.csv".format(kwargs['course_slug'],
                                         kwargs['semester_year'],
                                         kwargs['semester_type'])
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(
            filename)

        writer = csv.writer(response)
        headers = [
            "id",
            _("Last name"),
            _("First name"),
            _("Patronymic"),
            _("Branch"),
            _("Role"),
            _("Group"),
            _("Yandex Login"),
            _("Codeforces Handle"),
            "gitlab.manytask.org ID",
            "gitlab.manytask.org Login",
            _("Final grade"),
            _("Total"),
        ]
        for gradebook_assignment in gradebook.assignments.values():
            a = gradebook_assignment.assignment
            if gradebook.show_weight:
                title = f"{a.title} (вес: {a.weight})"
            else:
                title = a.title
            headers.append(title)
        writer.writerow(headers)
        students = [gs.student_profile.user_id for gs in gradebook.students.values()]
        services_queryset = (ConnectedAuthService.objects
                             .filter(user__in=students))
        connected_services = bucketize(services_queryset, key=lambda cs: cs.user_id)
        for gradebook_student in gradebook.students.values():
            student = gradebook_student.student
            student_profile = gradebook_student.student_profile
            student_group = gradebook_student.student_group
            connected_providers = connected_services.get(student.pk, [])
            connected_providers = {cp.provider: cp for cp in connected_providers}
            gitlab_manytask = connected_providers.get('gitlab-manytask')
            writer.writerow(
                itertools.chain(
                    [gradebook_student.enrollment_id,
                     student.last_name,
                     student.first_name,
                     student.patronymic,
                     student_profile.branch.name,
                     student_profile.get_type_display(),
                     (student_group and student_group.name) or "-",
                     student.yandex_login,
                     student.codeforces_login,
                     gitlab_manytask.uid if gitlab_manytask else "-",
                     gitlab_manytask.login if gitlab_manytask and gitlab_manytask.login else "-",
                     gradebook_student.final_grade_display,
                     gradebook_student.total_score],
                    [(a.score if a and a.score is not None else '')
                     for a in gradebook.submissions[gradebook_student.index]]))
        return response


class ImportAssignmentScoresBaseView(PermissionRequiredMixin, generic.View):
    course: Course
    permission_required = EditGradebook.name

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        queryset = (Course.objects
                    .filter(pk=kwargs['course_id'])
                    .select_related('meta_course', 'main_branch', 'semester'))
        self.course = get_object_or_404(queryset)

    def get_permission_object(self) -> Course:
        return self.course

    def post(self, request: AuthenticatedHttpRequest, *args: Any, **kwargs: Any):
        try:
            assignment_id = int(request.POST['assignment'])
            csv_file = request.FILES['csv_file']
        except (MultiValueDictKeyError, ValueError, TypeError):
            return HttpResponseBadRequest()
        try:
            assignment = (Assignment.objects
                          .select_related("course")
                          .get(course=self.course, pk=assignment_id))
        except Assignment.DoesNotExist:
            return HttpResponseBadRequest()
        self.import_scores(assignment, csv_file)
        return self.get_redirect_url()

    def import_scores(self, assignment, csv_file):
        try:
            found, imported = self._import_scores(assignment, csv_file)
            msg = _("Imported records for assignment {} - {} out of {}").format(
                assignment.title, imported, found)
            messages.info(self.request, msg)
        except ValidationError as e:
            msg = _('<b>Not all records were processed. '
                    'Import stopped by an error:</b><br>')
            messages.error(self.request, msg + e.message)
        except UnicodeDecodeError as e:
            messages.error(self.request, str(e))

    def _import_scores(self, assignment, csv_file):
        raise NotImplementedError

    def get_redirect_url(self):
        namespace = self.request.resolver_match.namespace
        url = self.course.get_gradebook_url(url_name=f'{namespace}:gradebook')
        return HttpResponseRedirect(url)


class ImportAssignmentScoresByStepikIDView(ImportAssignmentScoresBaseView):
    def _import_scores(self, assignment, csv_file):
        with_stepik_id = get_course_students_by_stepik_id(assignment.course_id)
        return assignment_import_scores_from_csv(assignment, csv_file,
                                                 required_headers=['stepic_id', 'score'],
                                                 enrolled_students=with_stepik_id,
                                                 lookup_column_name='stepic_id')


class ImportAssignmentScoresByYandexLoginView(ImportAssignmentScoresBaseView):
    def _import_scores(self, assignment, csv_file):
        with_yandex_login = get_course_students_by_yandex_login(assignment.course_id)
        return assignment_import_scores_from_csv(assignment, csv_file,
                                                 required_headers=['login', 'score'],
                                                 enrolled_students=with_yandex_login,
                                                 lookup_column_name='login',
                                                 transform=normalize_yandex_login)


class ImportAssignmentScoresByEnrollmentIDView(ImportAssignmentScoresBaseView):
    def _import_scores(self, assignment, csv_file):
        course_students = get_course_students(assignment.course_id)
        return assignment_import_scores_from_csv(assignment, csv_file,
                                                 required_headers=['id', 'score'],
                                                 enrolled_students=course_students,
                                                 lookup_column_name='id')


class GradebookImportScoresFromYandexContest(RolePermissionRequiredMixin, APIBaseView):
    """
    Imports assignment scores from Yandex.Contest problem defined in
    the assignment checker.
    """
    course: Course
    permission_classes = [EditGradebook]

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any):
        super().setup(request, *args, **kwargs)
        queryset = (Course.objects
                    .filter(pk=kwargs['course_id']))
        self.course = get_object_or_404(queryset)

    def get_permission_object(self) -> Course:
        return self.course

    class InputSerializer(serializers.Serializer):
        assignment = serializers.IntegerField()

    def post(self, request, *args: Any, **kwargs: Any):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        queryset = (Assignment.objects
                    .filter(pk=serializer.validated_data['assignment'],
                            course=self.course))
        assignment = get_object_or_404(queryset)

        checker = get_assignment_checker(assignment)
        access_token = checker.checking_system.settings['access_token']
        client = YandexContestAPI(access_token=access_token, refresh_token=access_token)

        assignment_import_scores_from_yandex_contest(client=client, assignment=assignment,
                                                     triggered_by=request.user)

        # TODO: return stats with updated/skipped/invalid/students without yandex login
        return Response(status=status.HTTP_201_CREATED, data={})

    def handle_exception(self, exc):
        if isinstance(exc, (Unavailable, ContestAPIError)):
            exc = cast_contest_error(exc)
        return super().handle_exception(exc)
