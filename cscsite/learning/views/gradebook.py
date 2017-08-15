import itertools
from collections import OrderedDict

import unicodecsv as csv
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views import generic

from core.exceptions import Redirect
from learning import utils
from learning.forms import GradeBookFormFactory, \
    MarksSheetTeacherImportGradesForm
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


# TODO: add transaction.atomic
# TODO: refactor with `gradebook` service
class GradeBookTeacherView(TeacherOnlyMixin, generic.FormView):
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
        try:
            semester_year = int(self.kwargs['semester_year'])
        except (ValueError, TypeError):
            raise Http404('Course offering not found')

        co_queryset = CourseOffering.objects
        if not self.request.user.is_curator:
            co_queryset = co_queryset.filter(teachers=self.request.user)
        # TODO: add tests
        city_code = self.kwargs['city'].lower()
        co_queryset = co_queryset.filter(city=city_code)
        try:
            course_offering = (co_queryset
                               .select_related('semester', 'course')
                               .get(course__slug=self.kwargs['course_slug'],
                                    semester__type=self.kwargs['semester_type'],
                                    semester__year=semester_year))
        except ObjectDoesNotExist:
            raise Http404('Course offering not found')
        self.course_offering = course_offering

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

        course_offering_list = (co_queryset
                                .order_by('-semester__year',
                                          '-semester__type',
                                          '-pk')
                                .select_related('semester', 'course'))
        self.course_offering_list = course_offering_list

        return (GradeBookFormFactory.build_form_class(student_assignments,
                                                      enrollment_list))

    def get_initial(self):
        return (GradeBookFormFactory
                .transform_to_initial(self.student_assignments,
                                      self.enrollment_list))

    def get_success_url(self):
        co = self.course_offering
        if self.is_for_staff:
            url_name = 'staff:course_markssheet_staff'
        else:
            url_name = 'markssheet_teacher'
        messages.info(self.request, _('Gradebook successfully saved.'),
                      extra_tags='timeout')
        return reverse(url_name, args=[co.get_city(),
                                       co.course.slug,
                                       co.semester.year,
                                       co.semester.type])

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
            self.recalculate_grading_type()
        return redirect(self.get_success_url())

    def recalculate_grading_type(self):
        """Update grading type for binded course offering if needed"""
        es = (Enrollment.active
              .filter(course_offering=self.course_offering)
              .values_list("grade", flat=True))
        grading_type = GRADING_TYPES.default
        if not any(filter(lambda g: g in [GRADES.good, GRADES.excellent], es)):
            grading_type = GRADING_TYPES.binary
        if self.course_offering.grading_type != grading_type:
            self.course_offering.grading_type = grading_type
            self.course_offering.save()

    def get_context_data(self, *args, **kwargs):
        context = (super(GradeBookTeacherView, self)
                   .get_context_data(*args, **kwargs))
        context['course_offering'] = self.course_offering
        context['course_offering_list'] = self.course_offering_list
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
        course_slug = kwargs['course_slug']
        semester_slug = kwargs['semester_slug']
        try:
            semester_year, semester_type = semester_slug.split('-')
            semester_year = int(semester_year)
        except (ValueError, TypeError):
            raise Http404('Course offering not found')
        if request.user.is_authenticated and request.user.is_curator:
            base_qs = CourseOffering.objects
        else:
            base_qs = CourseOffering.objects.filter(teachers=request.user)

        # TODO: add tests
        city_code = self.kwargs['city'].lower()
        base_qs = base_qs.filter(city=city_code)

        try:
            co = base_qs.get(
                course__slug=course_slug,
                semester__type=semester_type,
                semester__year=semester_year)
        except ObjectDoesNotExist:
            raise Http404('Course offering not found')
        a_ss = (StudentAssignment.objects
                .filter(assignment__course_offering=co)
                .order_by('student', 'assignment')
                .select_related('assignment',
                                'assignment__course_offering',
                                'assignment__course_offering__course',
                                'assignment__course_offering__semester',
                                'student'))
        enrollments = (Enrollment.active
                       .filter(course_offering=co)
                       .select_related('course_offering', 'student'))
        structured = OrderedDict()
        enrollment_grades = {}
        for enrollment in enrollments:
            student = enrollment.student
            enrollment_grades[student] = enrollment.grade_display
            if student not in structured:
                structured[student] = OrderedDict()
        for a_s in a_ss:
            if a_s.student not in structured:
                continue  # student isn't enrolled
            structured[a_s.student][a_s.assignment] = a_s.grade

        header = structured.values()
        # FIXME: raise StopIteration if no students found. Add test
        header = next(iter(header)).keys()
        for _, by_assignment in structured.items():
            # we should check for "assignment consistency": that all
            # assignments are similar for all students in particular
            # course offering
            assert by_assignment.keys() == header

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename \
            = "{}-{}.csv".format(kwargs['course_slug'],
                                 kwargs['semester_slug'])
        response['Content-Disposition'] \
            = 'attachment; filename="{}"'.format(filename)

        writer = csv.writer(response)
        writer.writerow(['Фамилия',
                         'Имя',
                         'Яндекс ID'] +
                        [a.title for a in header] +
                        ['Итоговая оценка'])
        for student, by_assignment in structured.items():
            writer.writerow(
                [(x if x is not None else '') for x in
                 itertools.chain([student.last_name, student.first_name,
                                  student.yandex_id],
                                 by_assignment.values(),
                                 [enrollment_grades[student]])])
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