import itertools
from typing import Optional

import unicodecsv as csv
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Prefetch
from django.http import HttpResponseRedirect, Http404, HttpResponse, \
    HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import redirect
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from vanilla import FormView

from core.exceptions import Redirect
from learning import utils
from learning.gradebook import GradeBookFormFactory, gradebook_data, \
    AssignmentGradesImport
from learning.models import Semester, Course, Assignment
from learning.settings import SEMESTER_AUTUMN_SPRING_INDEX_OFFSET
from learning.utils import get_current_term_pair, get_term_index
from learning.viewmixins import CuratorOnlyMixin, TeacherOnlyMixin

__all__ = [
    "GradeBookCuratorDispatchView", "GradeBookTeacherDispatchView",
    "GradeBookTeacherView",
    "GradeBookTeacherCSVView", "AssignmentGradesImportByStepikIDView",
    "AssignmentGradesImportByYandexLoginView"
]


class _GradeBookDispatchView(generic.ListView):
    model = Semester

    def get_co_queryset(self):
        return (Course.objects
                .select_related("meta_course")
                .order_by("meta_course__name"))

    def get_queryset(self):
        # FIXME: Is it ok to use 'spb' here?
        current_year, term_type = get_current_term_pair('spb')
        term_index = get_term_index(current_year, term_type)
        # Skip to spring semester
        # FIXME: why?!
        if term_type == Semester.TYPES.autumn:
            term_index += SEMESTER_AUTUMN_SPRING_INDEX_OFFSET
        return (Semester.objects
                .filter(index__lte=term_index)
                .exclude(type=Semester.TYPES.summer)
                .prefetch_related(
                    Prefetch(
                        "courseoffering_set",
                        queryset=self.get_co_queryset(),
                        to_attr="courseofferings"
                    )))


class GradeBookCuratorDispatchView(CuratorOnlyMixin, _GradeBookDispatchView):
    template_name = "learning/gradebook/list_curator.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        semester_list = list(context["semester_list"])
        if not semester_list:
            return context
        # Add stub spring term if we have only the fall term for the ongoing
        # academic year
        current = semester_list[0]
        if current.type == Semester.TYPES.autumn:
            term = Semester(type=Semester.TYPES.spring, year=current.year + 1)
            term.courseofferings = []
            semester_list.insert(0, term)
        context["semester_list"] = [(a, s) for s, a in
                                    utils.grouper(semester_list, 2)]
        return context


class GradeBookTeacherDispatchView(TeacherOnlyMixin, _GradeBookDispatchView):
    """
    Redirect teacher to appropriate gradebook page if he has only
    one course offering in current term.
    """
    template_name = "learning/gradebook/list_teacher.html"

    def get_co_queryset(self):
        qs = super().get_co_queryset()
        return qs.filter(teachers=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # FIXME: Is it ok to use 'spb' here?
        current_year, term_type = get_current_term_pair('spb')
        current_term_index = get_term_index(current_year, term_type)
        co_count = 0
        for semester in context["semester_list"]:
            if semester.index == current_term_index:
                if len(semester.courseofferings) == 1:
                    co = semester.courseofferings[0]
                    raise Redirect(to=co.get_gradebook_url())
            co_count += len(semester.courseofferings)
        if not co_count:
            context["semester_list"] = []
        return context


def _get_course_offering(get_params, user) -> Optional[Course]:
    try:
        filter_kwargs = dict(
            city=get_params['city'].lower(),
            meta_course__slug=get_params['course_slug'],
            semester__type=get_params['semester_type'],
            semester__year=int(get_params['semester_year'])
        )
        if not user.is_curator:
            filter_kwargs["teachers"] = user
        return (Course.objects
                .select_related('semester', 'meta_course')
                .get(**filter_kwargs))
    except (ValueError, KeyError, AttributeError, ObjectDoesNotExist):
        return None


class GradeBookTeacherView(TeacherOnlyMixin, FormView):
    is_for_staff = False
    user_type = 'teacher'
    template_name = "learning/gradebook/form.html"
    context_object_name = 'assignment_list'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = None
        self.course_offering = None
        self.is_for_staff = kwargs.get('is_for_staff', False)

    def get_form(self, data=None, files=None, **kwargs):
        cls = self.get_form_class()
        # Set initial data for all GET-requests
        if not data and "initial" not in kwargs:
            initial = GradeBookFormFactory.transform_to_initial(self.data)
            kwargs["initial"] = initial
        return cls(data=data, files=files, **kwargs)

    def get_form_class(self):
        if self.course_offering is None:
            self.course_offering = _get_course_offering(self.kwargs,
                                                        self.request.user)
        if self.course_offering is None:
            raise Http404('Course offering not found')
        self.data = gradebook_data(self.course_offering)
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
            self.data = gradebook_data(self.course_offering)
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
        return self.data.course_offering.get_gradebook_url(
            for_curator=self.is_for_staff)

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
        # List of user gradebooks
        # TODO: Move to the model
        filter_kwargs = {}
        if not self.request.user.is_curator:
            filter_kwargs["teachers"] = self.request.user
        course_offering_list = (Course.objects
                                .filter(**filter_kwargs)
                                .order_by('-semester__index',
                                          '-pk')
                                .select_related('semester', 'meta_course'))
        context['course_offering_list'] = course_offering_list
        context['user_type'] = self.user_type

        return context


class GradeBookTeacherCSVView(TeacherOnlyMixin, generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        course_offering = _get_course_offering(self.kwargs, request.user)
        if course_offering is None:
            raise Http404('Course offering not found')

        data = gradebook_data(course_offering)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = "{}-{}-{}.csv".format(kwargs['course_slug'],
                                         kwargs['semester_year'],
                                         kwargs['semester_type'])
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(
            filename)

        writer = csv.writer(response)
        writer.writerow(data.get_headers())
        for student in data.students.values():
            writer.writerow(
                itertools.chain(
                    [student.last_name,
                     student.first_name,
                     student.final_grade_display,
                     student.total_score],
                    [(a.score if a and a.score is not None else '')
                     for a in data.submissions[student.index]]))
        return response


class AssignmentGradesImportGenericView(TeacherOnlyMixin, generic.View):
    def post(self, request, course_offering_pk, *args, **kwargs):
        try:
            assignment_id = int(request.POST['assignment'])
            csv_file = request.FILES['csv_file']
        except (MultiValueDictKeyError, ValueError, TypeError):
            return HttpResponseBadRequest()
        filters = {
            "pk": assignment_id,
            "course_offering_id": course_offering_pk,
            "is_online": False
        }
        if not request.user.is_curator:
            filters['course_offering__teachers__id'] = request.user.pk
        try:
            assignment = (Assignment.objects
                          .select_related("course_offering")
                          .get(**filters))
            total, success = self.import_grades_for_assignment(assignment)
            messages.info(self.request,
                          _("Successfully imported {} results").format(success))
        except ValidationError as e:
            messages.error(self.request, e.message)
        except Assignment.DoesNotExist:
            return HttpResponseForbidden()
        url = assignment.course_offering.get_gradebook_url()
        return HttpResponseRedirect(url)

    def import_grades_for_assignment(self, assignment):
        raise NotImplementedError()


class AssignmentGradesImportByStepikIDView(AssignmentGradesImportGenericView):
    def import_grades_for_assignment(self, assignment):
        csv_file = self.request.FILES['csv_file']
        return AssignmentGradesImport(assignment, csv_file, "stepic_id").process()


class AssignmentGradesImportByYandexLoginView(AssignmentGradesImportGenericView):
    def import_grades_for_assignment(self, assignment):
        csv_file = self.request.FILES['csv_file']
        return AssignmentGradesImport(assignment, csv_file, "yandex_id").process()
