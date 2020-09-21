import csv
import itertools

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Q
from django.http import HttpResponseRedirect, HttpResponse, \
    HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import redirect, get_object_or_404
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.translation import gettext_lazy as _
from django.views import generic
from vanilla import FormView

from auth.mixins import PermissionRequiredMixin
from courses.constants import SemesterTypes
from courses.models import Course, Semester, Assignment, \
    AssignmentSubmissionFormats
from courses.utils import get_current_term_pair
from courses.views.mixins import CourseURLParamsMixin
from learning.gradebook import GradeBookFormFactory, gradebook_data
from learning.gradebook.imports import import_assignment_scores, \
    get_course_students_by_stepik_id, get_course_students_by_yandex_login, \
    get_course_students
from learning.permissions import ViewOwnGradebook, EditGradebook
from users.mixins import TeacherOnlyMixin

__all__ = [
    "GradeBookView",
    "GradeBookCSVView", "ImportAssignmentScoresByStepikIDView",
    "ImportAssignmentScoresByYandexLoginView"
]


class GradeBookListBaseView(generic.ListView):
    model = Semester

    def get_course_queryset(self):
        return (Course.objects
                .available_on_site(self.request.site)
                .select_related("meta_course", "main_branch")
                .order_by("meta_course__name"))

    def get_term_threshold(self):
        tz = self.request.user.get_timezone()
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


class GradeBookView(PermissionRequiredMixin, CourseURLParamsMixin, FormView):
    is_for_staff = False
    user_type = 'teacher'
    template_name = "learning/gradebook/gradebook_form.html"
    context_object_name = 'assignment_list'
    permission_required = ViewOwnGradebook.name

    def get_permission_object(self):
        return self.course

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = None
        self.is_for_staff = kwargs.get('is_for_staff', False)

    def get_form(self, data=None, files=None, **kwargs):
        cls = self.get_form_class()
        # Set initial data for all GET-requests
        if not data and "initial" not in kwargs:
            initial = GradeBookFormFactory.transform_to_initial(self.data)
            kwargs["initial"] = initial
        return cls(data=data, files=files, **kwargs)

    def get_form_class(self):
        self.data = gradebook_data(self.course)
        return GradeBookFormFactory.build_form_class(self.data)

    def form_valid(self, form):
        conflicts_on_save = form.save()
        if conflicts_on_save:
            msg = _("<b>Внимание, часть данных не была сохранена!</b><br>"
                    "В процессе редактирования данные были "
                    "изменены другими участниками. Необходимо вручную "
                    "разрешить конфликты и повторить отправку формы.")
            messages.warning(self.request, msg)
            # Replace form data with actual db values and user input
            # for conflict fields
            self.data = gradebook_data(self.course)
            current_data = GradeBookFormFactory.transform_to_initial(self.data)
            data = form.data.copy()
            for k, v in current_data.items():
                if k not in data:
                    data[k] = v
            form.data = data
            return super().form_invalid(form)
        return redirect(self.get_success_url())

    def get_success_url(self):
        messages.success(self.request,
                         _('Gradebook successfully saved.'),
                         extra_tags='timeout')
        if self.is_for_staff:
            params = {"url_name": "staff:gradebook"}
        else:
            params = {}
        return self.data.course.get_gradebook_url(**params)

    def form_invalid(self, form):
        """
        Append initial to form.data since we didn't sent full image of
        form data in POST-request, but only changed data
        """
        msg = _("Gradebook hasn't been saved.")
        messages.error(self.request, msg)
        initial = GradeBookFormFactory.transform_to_initial(self.data)
        data = form.data.copy()
        for k, v in initial.items():
            if k not in data:
                data[k] = v
        form.data = data
        return super().form_invalid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gradebook"] = self.data
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
    permission_required = ViewOwnGradebook.name

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
            _("Branch"),
            _("Role"),
            _("Group"),
            _("Yandex Login"),
            _("Codeforces Handle"),
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
        for gradebook_student in gradebook.students.values():
            student = gradebook_student.student
            student_profile = gradebook_student.student_profile
            student_group = gradebook_student.student_group
            writer.writerow(
                itertools.chain(
                    [gradebook_student.enrollment_id,
                     student.last_name,
                     student.first_name,
                     student_profile.branch.name,
                     student_profile.get_type_display(),
                     student_group.name,
                     student.yandex_login,
                     student.codeforces_login,
                     gradebook_student.final_grade_display,
                     gradebook_student.total_score],
                    [(a.score if a and a.score is not None else '')
                     for a in gradebook.submissions[gradebook_student.index]]))
        return response


class ImportAssignmentScoresBaseView(PermissionRequiredMixin, generic.View):
    permission_required = EditGradebook.name

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        course_id = kwargs['course_id']
        self.course = get_object_or_404(Course.objects.filter(pk=course_id))

    def get_permission_object(self):
        return self.course

    def post(self, request, *args, **kwargs):
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
        csv_file = self.request.FILES['csv_file']
        with_stepik_id = get_course_students_by_stepik_id(assignment.course_id)
        return import_assignment_scores(assignment, csv_file,
                                        required_headers=['stepic_id', 'score'],
                                        enrolled_students=with_stepik_id,
                                        lookup_column_name='stepic_id')


class ImportAssignmentScoresByYandexLoginView(ImportAssignmentScoresBaseView):
    def _import_scores(self, assignment, csv_file):
        with_yandex_login = get_course_students_by_yandex_login(assignment.course_id)
        return import_assignment_scores(assignment, csv_file,
                                        required_headers=['yandex_login', 'score'],
                                        enrolled_students=with_yandex_login,
                                        lookup_column_name='yandex_login')


class ImportAssignmentScoresByEnrollmentIDView(ImportAssignmentScoresBaseView):
    def _import_scores(self, assignment, csv_file):
        course_students = get_course_students(assignment.course_id)
        return import_assignment_scores(assignment, csv_file,
                                        required_headers=['id', 'score'],
                                        enrolled_students=course_students,
                                        lookup_column_name='id')
