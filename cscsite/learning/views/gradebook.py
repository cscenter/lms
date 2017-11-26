import itertools
from collections import OrderedDict
from typing import Optional

import unicodecsv as csv
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from vanilla import FormView

from core.exceptions import Redirect
from learning import utils
from learning.forms import MarksSheetTeacherImportGradesForm
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



# TODO: add transaction.atomic
# TODO: refactor with `gradebook` service
class GradeBookTeacherView(TeacherOnlyMixin, FormView):
    is_for_staff = False
    user_type = 'teacher'
    template_name = "learning/gradebook/form.html"
    context_object_name = 'assignment_list'

    def __init__(self, *args, **kwargs):
        self.student_assignments = None
        self.enrollment_list = None
        self.course_offering_list = None
        self.course_offering = None
        super().__init__(*args, **kwargs)
        self.is_for_staff = kwargs.get('is_for_staff', False)

    def get_form_class(self):
        course_offering = _get_course_offering(self.kwargs, self.request.user)
        if course_offering is None:
            raise Http404('Course offering not found')
        self.course_offering = course_offering

        data = gradebook_data(course_offering)

        # Sacrifice attributes access for better performance
        student_assignments = (
            StudentAssignment.objects
                .filter(assignment__course_offering=course_offering)
                .values("pk",
                        "grade",
                        "first_submission_at",
                        "assignment__pk",
                        "assignment__title",
                        "assignment__is_online",
                        "assignment__grade_max",
                        "assignment__grade_min",
                        "student__pk")
                .order_by("assignment__pk",
                          "student__pk")
        )
        self.student_assignments = student_assignments

        enrollment_list = (Enrollment.active
                           .filter(course_offering=course_offering)
                           .select_related("student"))
        self.enrollment_list = enrollment_list

        return GradeBookFormFactory.build_form_class(data)

    def get_initial(self):
        return (GradeBookFormFactory
                .transform_to_initial(self.student_assignments,
                                      self.enrollment_list))

    def get_success_url(self):
        messages.info(self.request,
                      _('Gradebook successfully saved.'),
                      extra_tags='timeout')
        return self.course_offering.get_gradebook_url(
            for_curator=self.is_for_staff)

    def form_valid(self, form):
        a_s_index, enrollment_index = \
            GradeBookFormFactory.build_indexes(self.student_assignments,
                                               self.enrollment_list)
        final_grade_updated = False
        for field in form.changed_data:
            if field in a_s_index:
                a_s = a_s_index[field]
                StudentAssignment.objects.filter(pk=a_s["pk"]).update(
                    grade=form.cleaned_data[field])
                continue
            # Looking for final_grade_*
            elif field in enrollment_index:
                final_grade_updated = True
                enrollment = enrollment_index[field]
                enrollment.grade = form.cleaned_data[field]
                enrollment.save()
                continue
        if final_grade_updated:
            self.course_offering.recalculate_grading_type()
        return redirect(self.get_success_url())

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['course_offering'] = self.course_offering
        # List of user gradebooks
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

        students = OrderedDict()
        assignments = OrderedDict()

        def get_final_grade_widget(enrollment_pk):
            key = GradeBookFormFactory.FINAL_GRADE_PREFIX.format(enrollment_pk)
            return context['form'][key]

        for enrollment in self.enrollment_list:
            student_id = enrollment.student_id
            if student_id not in students:
                students[student_id] = OrderedDict({
                    "student": enrollment.student,
                    "grade": get_final_grade_widget(enrollment.pk),
                    "total": 0
                })

        for a_s in self.student_assignments:
            student_id = a_s["student__pk"]
            assignment_id = a_s["assignment__pk"]
            # The student unsubscribed from the course
            if student_id not in students:
                continue

            if assignment_id not in assignments:
                assignments[assignment_id] = {
                    "header": {
                        "pk": a_s["assignment__pk"],
                        "title": a_s["assignment__title"],
                        "is_online": a_s["assignment__is_online"],
                        "grade_min": a_s["assignment__grade_min"],
                        "grade_max": a_s["assignment__grade_max"],
                    },
                    "students": OrderedDict(((sid, None) for sid in students))
                }
            assignment = assignments[assignment_id]

            state = None
            # FIXME: duplicated logic from is_passed method!
            a_s["is_passed"] = a_s["first_submission_at"] is not None
            if assignment["header"]["is_online"]:
                state_value = StudentAssignment.calculate_state(
                    a_s["grade"],
                    assignment["header"]["is_online"],
                    a_s["is_passed"],
                    assignment["header"]["grade_min"],
                    assignment["header"]["grade_max"],
                )
                if a_s["grade"] is not None:
                    state = "{0}/{1}".format(a_s["grade"],
                                             assignment["header"]["grade_max"])
                else:
                    state = StudentAssignment.SHORT_STATES[state_value]
            assignment["students"][student_id] = {
                "pk": a_s["pk"],
                "grade": a_s["grade"] if a_s["grade"] is not None else "",
                "is_passed": a_s["is_passed"],  # FIXME: useless?
                "state": state
            }

            if a_s["grade"] is not None:
                students[student_id]["total"] += int(a_s["grade"])

        for assignment in assignments.values():
            # we should check for "assignment consistency": that all
            # student assignments are presented
            # FIXME: what about (923, None)? Is it ok?
            assert any(s is not None for s in assignment["students"])

        context['students'] = students
        context['assignments'] = assignments
        # Magic "100" constant - width of .assignment column
        context['assignments_width'] = len(assignments) * 100

        return context


class GradeBookTeacherCSVView(TeacherOnlyMixin,
                              generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        course_offering = _get_course_offering(self.kwargs, request.user)
        if course_offering is None:
            raise Http404('Course offering not found')

        data = gradebook_data(course_offering)

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename \
            = "{}-{}-{}.csv".format(kwargs['course_slug'],
                                    kwargs['semester_year'],
                                    kwargs['semester_type'])
        response['Content-Disposition'] \
            = 'attachment; filename="{}"'.format(filename)

        writer = csv.writer(response)
        common_headers = ['Фамилия', 'Имя', 'Яндекс ID']
        writer.writerow(common_headers +
                        [a.title for a in data.assignments.values()] +
                        ['Итоговая оценка'])

        for index, student in enumerate(data.students.values()):
            writer.writerow(
                itertools.chain(
                    [student.last_name, student.first_name, student.yandex_id],
                    [(a["score"] if a and a["score"] is not None else '')
                     for a in data.submissions[index]],
                    [student.final_grade_display]))
        return response


class GradeBookTeacherImportCSVFromStepicView(TeacherOnlyMixin, generic.View):
    """Import students grades from stepic platform"""

    def post(self, request, course_offering_pk, *args, **kwargs):
        filters = {"pk": course_offering_pk}
        if not request.user.is_curator:
            filters['teachers__in'] = [request.user.pk]
        co = get_object_or_404(CourseOffering, **filters)
        url = co.get_gradebook_url()
        form = MarksSheetTeacherImportGradesForm(
            request.POST, request.FILES, course_id=co.course_id)
        if form.is_valid():
            assignment = form.cleaned_data['assignment']
            ImportGradesByStepicID(request, assignment).process()
        else:
            # TODO: provide better description
            messages.info(request, _('Invalid form.'))
        return HttpResponseRedirect(url)


class GradeBookTeacherImportCSVFromYandexView(TeacherOnlyMixin, generic.View):
    """Import students grades by yandex login"""

    def post(self, request, *args, **kwargs):
        filter = dict(pk=self.kwargs.get('course_offering_pk'))
        if not request.user.is_authenticated or not request.user.is_curator:
            filter['teachers__in'] = [request.user.pk]
        co = get_object_or_404(CourseOffering, **filter)
        url = co.get_gradebook_url()
        form = MarksSheetTeacherImportGradesForm(
            request.POST, request.FILES, course_id=co.course_id)
        if form.is_valid():
            assignment = form.cleaned_data['assignment']
            ImportGradesByYandexLogin(request, assignment).process()
        else:
            # TODO: provide better description
            messages.info(request, _('Invalid form.'))
        return HttpResponseRedirect(url)