import csv
import statistics
from datetime import datetime
from django.db.models import Prefetch, Q
from django.http.response import HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.utils import timezone

import core.utils
from core.utils import bucketize
from courses.constants import SemesterTypes
from courses.models import Course, Semester, CourseDurations
from courses.utils import date_to_term_pair
from courses.views.mixins import CourseURLParamsMixin
from learning.models import Enrollment
from learning.settings import GradeTypes, StudentStatuses
from users.mixins import CuratorOnlyMixin
from users.models import StudentProfile, StudentTypes, User

class EnroleesSelectionListView(CuratorOnlyMixin, generic.ListView):
    template_name = "staff/enrolees_selection_list.html"
    model = Semester

    def get_course_queryset(self):
        return (Course.objects
                .available_on_site(self.request.site)
                # TODO add selection_avaliable filter
                .select_related("meta_course", "main_branch")
                .order_by("meta_course__name"))

    def get_term_threshold(self):
        latest_term = Semester.objects.order_by("-index").first()
        return latest_term.index
    
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

    def get_context_data(self, **kwargs):
        semester_list = list(self.object_list)
        # Add stub term if we have only 1 term for the ongoing academic year
        if semester_list:
            current = semester_list[0]
            if current.type == SemesterTypes.AUTUMN:
                next_term = current.term_pair.get_next()
                term = Semester(type=next_term.type, year=next_term.year)
                term.course_offerings = []
                semester_list.insert(0, term)
            semester_list = [(a, s) for s, a in core.utils.chunks(semester_list, 2)]
            for academic_year in semester_list:
                # Group by main branch name
                for term in academic_year:
                    courses = bucketize(
                        term.course_offerings, key=lambda c: c.main_branch.name
                    )
                    term.course_offerings = courses
        context = {
            'CourseDurations': CourseDurations,
            "semester_list": semester_list
        }
        return context
    
class EnroleesSelectionCSVView(CuratorOnlyMixin, CourseURLParamsMixin,
                       generic.base.View):

    grade_to_numeric = {
        GradeTypes.CREDIT: 3,
        GradeTypes.GOOD: 4,
        GradeTypes.EXCELLENT: 5
    }
        

    def calculate_average_grades(self, students):
        for student in students:
            enrollments = [enrollment for profile in student.official_profiles for enrollment in profile.enrollment_set.all()]
            numeric_satisfactory_grades = [self.grade_to_numeric[enrollment.grade] for enrollment in enrollments 
                                           if enrollment.grade in self.grade_to_numeric and enrollment.course.is_visible_in_certificates]
            if not numeric_satisfactory_grades:
                yield student.id, ""
            else:
                yield student.id, round(statistics.fmean(numeric_satisfactory_grades), 3)
        
    def get(self, request, *args, **kwargs):
        enrollments = Enrollment.active.filter(course=self.course).select_related("student", "student_profile__branch", "student_profile__partner").order_by("student")
        student_profile_queryset = (StudentProfile.objects
                       .filter(site=request.site, 
                               type__in=[StudentTypes.REGULAR, StudentTypes.PARTNER],
                               status__ne=StudentStatuses.EXPELLED)
                       .order_by('year_of_admission', '-pk')
                       .select_related("branch")
                       .prefetch_related("enrollment_set__course"))
        users = (User.objects
            .filter(pk__in=enrollments.values_list("student__id", flat=True))
            .prefetch_related(Prefetch("student_profiles", queryset=student_profile_queryset, to_attr="official_profiles")))
            
        average_grades_map = dict(self.calculate_average_grades(users))
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = "{}-{}-{}-enrolees-selection.csv".format(kwargs['course_slug'],
                                         kwargs['semester_year'],
                                         kwargs['semester_type'])
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        headers = [
            _("User url"),
            _("Last name"),
            _("First name"),
            _("Patronymic"),
            _("Branch"),
            _("Student type"),
            _("Partner"),
            _("Curriculum year"),
            _("Enrollment type"),
            _("Entry reason"),
            _("Average grade")
        ]
        writer.writerow(headers)
        for enrollment in enrollments:
            student = enrollment.student
            student_profile = enrollment.student_profile
            writer.writerow([
                student.get_absolute_url(), student.last_name, student.first_name, student.patronymic,
                student_profile.branch.name, student_profile.get_type_display(), student_profile.partner, student_profile.year_of_curriculum,
                enrollment.get_type_display(), enrollment.reason_entry, average_grades_map[student.id]
            ])
        return response