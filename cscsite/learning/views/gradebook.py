import itertools
from typing import Optional

import unicodecsv as csv
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from vanilla import FormView

from core.exceptions import Redirect
from learning import utils
from learning.forms import GradebookImportCSVForm
from learning.gradebook import GradeBookFormFactory, gradebook_data
from learning.management.imports import ImportGradesByStepicID, \
    ImportGradesByYandexLogin
from learning.models import Semester, CourseOffering, StudentAssignment, \
    Enrollment
from learning.settings import SEMESTER_AUTUMN_SPRING_INDEX_OFFSET, \
    GRADING_TYPES, GRADES
from learning.utils import get_current_term_pair, get_term_index
from learning.viewmixins import CuratorOnlyMixin, TeacherOnlyMixin

__all__ = [
    "GradeBookCuratorDispatchView", "GradeBookTeacherDispatchView",
    "GradeBookTeacherView",
    "GradeBookTeacherCSVView", "GradeBookTeacherImportCSVFromStepicView",
    "GradeBookTeacherImportCSVFromYandexView"
]


class _GradeBookDispatchView(generic.ListView):
    model = Semester

    def get_co_queryset(self):
        return (CourseOffering.objects
                .select_related("course")
                .order_by("course__name"))

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


def _get_course_offering(get_params, user) -> Optional[CourseOffering]:
    # TODO: add tests
    try:
        filter_kwargs = dict(
            city=get_params['city'].lower(),
            course__slug=get_params['course_slug'],
            semester__type=get_params['semester_type'],
            semester__year=int(get_params['semester_year'])
        )
        if not user.is_curator:
            filter_kwargs["teachers"] = user
        return (CourseOffering.objects
                .select_related('semester', 'course')
                .get(**filter_kwargs))
    except (ValueError, ObjectDoesNotExist):
        return None


class GradeBookTeacherView(TeacherOnlyMixin, FormView):
    is_for_staff = False
    user_type = 'teacher'
    template_name = "learning/gradebook/form.html"
    context_object_name = 'assignment_list'

    def __init__(self, *args, **kwargs):
        self.course_offering = None
        super().__init__(*args, **kwargs)
        self.is_for_staff = kwargs.get('is_for_staff', False)

    def get_form(self, data=None, files=None, **kwargs):
        cls = self.get_form_class()
        if "initial" not in kwargs:
            initial = GradeBookFormFactory.transform_to_initial(self.data)
            kwargs["initial"] = initial
        return cls(data=data, files=files, **kwargs)

    def get_form_class(self):
        course_offering = _get_course_offering(self.kwargs, self.request.user)
        if course_offering is None:
            raise Http404('Course offering not found')
        self.course_offering = course_offering
        self.data = gradebook_data(course_offering)
        return GradeBookFormFactory.build_form_class(self.data)

    def get_success_url(self):
        messages.info(self.request,
                      _('Gradebook successfully saved.'),
                      extra_tags='timeout')
        return self.course_offering.get_gradebook_url(
            for_curator=self.is_for_staff)

    def form_valid(self, form):
        # TODO: add transaction.atomic
        final_grade_updated = False
        for field_name in form.changed_data:
            if field_name.startswith(form.GRADE_PREFIX):
                field = form.fields[field_name]
                (StudentAssignment.objects
                    .filter(pk=field.student_assignment_id)
                    .update(grade=form.cleaned_data[field_name]))
            elif field_name.startswith(form.FINAL_GRADE_PREFIX):
                field = form.fields[field_name]
                final_grade_updated = True
                (Enrollment.objects
                    .filter(pk=field.enrollment_id)
                    .update(grade=form.cleaned_data[field_name]))
        if final_grade_updated:
            self.course_offering.recalculate_grading_type()
        return redirect(self.get_success_url())

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["gradebook"] = self.data
        context['course_offering'] = self.course_offering
        # List of user gradebooks
        # TODO: Move to the model
        filter_kwargs = {}
        if not self.request.user.is_curator:
            filter_kwargs["teachers"] = self.request.user
        course_offering_list = (CourseOffering.objects
                                .filter(**filter_kwargs)
                                .order_by('-semester__year',
                                          '-semester__type',
                                          '-pk')
                                .select_related('semester', 'course'))
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


class GradeBookTeacherImportCSVFromStepicView(TeacherOnlyMixin, generic.View):
    """Import students grades from stepic platform"""

    def post(self, request, course_offering_pk, *args, **kwargs):
        filters = {"pk": course_offering_pk}
        if not request.user.is_curator:
            filters['teachers__in'] = [request.user.pk]
        co = get_object_or_404(CourseOffering, **filters)
        form = GradebookImportCSVForm(request.POST, request.FILES,
                                      course_id=co.course_id)
        if form.is_valid():
            assignment = form.cleaned_data['assignment']
            ImportGradesByStepicID(request, assignment).import_data()
        else:
            # TODO: provide better description
            messages.info(request, _('Invalid form.'))
        url = co.get_gradebook_url()
        return HttpResponseRedirect(url)


class GradeBookTeacherImportCSVFromYandexView(TeacherOnlyMixin, generic.View):
    """Import students grades by yandex login"""

    def post(self, request, course_offering_pk, *args, **kwargs):
        filters = {"pk": course_offering_pk}
        if not request.user.is_curator:
            filters['teachers__in'] = [request.user.pk]
        co = get_object_or_404(CourseOffering, **filters)
        form = GradebookImportCSVForm(request.POST, request.FILES,
                                      course_id=co.course_id)
        if form.is_valid():
            assignment = form.cleaned_data['assignment']
            ImportGradesByYandexLogin(request, assignment).import_data()
        else:
            # TODO: provide better description
            messages.info(request, _('Invalid form.'))
        url = co.get_gradebook_url()
        return HttpResponseRedirect(url)
