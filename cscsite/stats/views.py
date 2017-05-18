import json

import itertools
from collections import OrderedDict

from django.urls import reverse
from django.db.models import Prefetch
from django.views import generic
from rest_framework.views import APIView
from rest_framework.response import Response

from api.permissions import CuratorAccessPermission
from learning.models import Course, Semester, CourseOffering, StudentAssignment, \
    Assignment, Enrollment
from learning.reports import ProgressReportForDiplomas
from learning.settings import CENTER_FOUNDATION_YEAR, SEMESTER_TYPES, GRADES
from learning.utils import get_term_index
from learning.viewmixins import CuratorOnlyMixin
from stats.serializers import ParticipantsStatsSerializer, \
    AssignmentsStatsSerializer, EnrollmentsStatsSerializer
from users.models import CSCUser


class StatsIndexView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "stats/index.html"

    def get_context_data(self, **kwargs):
        context = super(StatsIndexView, self).get_context_data(**kwargs)
        # Terms grouped by year
        term_start = get_term_index(CENTER_FOUNDATION_YEAR,
                                    SEMESTER_TYPES.autumn)
        terms_grouped = itertools.groupby(
            Semester.objects.only("pk", "type", "year")
                    .filter(index__gte=term_start)
                    .order_by("-index"),
            key=lambda x: x.year)
        context["terms"] = [(g_name, list(g)) for g_name, g in terms_grouped]
        # TODO: Если прикрутить REST API, то можно эту логику перенести
        # на клиент и сразу не грузить весь список курсов
        # Courses grouped by term
        courses_grouped = itertools.groupby(
            CourseOffering.objects
                .filter(is_open=False)
                .values("pk", "semester_id", "course__name")
                .order_by("-semester_id", "course__name"),
            key=lambda x: x["semester_id"])
        courses = {term_id: list(cs) for term_id, cs in courses_grouped}
        # Find selected course and term
        course_session_id = self.request.GET.get("course_session_id")
        try:
            course_session_id = int(course_session_id)
        except TypeError:
            max_term_id = max(courses.keys())
            course_session_id = courses[max_term_id][0]["pk"]
        term_id = None
        for group in courses.values():
            for co in group:
                if co["pk"] == course_session_id:
                    term_id = co["semester_id"]
                    break
        if not term_id:
            # Replace with appropriate error
            raise Exception("{}".format(course_session_id))

        context["courses"] = courses
        context["data"] = {
            "selected": {
                "term_id": term_id,
                "course_session_id": course_session_id,
            },
        }

        context["json_data"] = json.dumps({
            "courses": courses,
            "course_session_id": course_session_id,
        })
        return context


# TODO: rewrite with read-only api view? (see example in docs)
class CourseParticipantsStatsByGroup(APIView):
    """
    Aggregate stats about course offering participants.
    """
    http_method_names = ['get']
    permission_classes = [CuratorAccessPermission]

    def get(self, request, course_session_id, format=None):
        participants = (CSCUser.objects
                        .only("curriculum_year")
                        .filter(
            enrollment__course_offering_id=course_session_id)
                        .prefetch_related("groups")
                        .order_by())

        serializer = ParticipantsStatsSerializer(participants, many=True)
        return Response(serializer.data)


class AssignmentsStats(APIView):
    """
    Aggregate stats about course offering assignment progress.
    """
    http_method_names = ['get']
    permission_classes = [CuratorAccessPermission]

    def get(self, request, course_session_id, format=None):
        assignments = (Assignment
                       .objects
                       .only("pk", "title", "course_offering_id", "deadline_at",
                             "grade_min", "grade_max", "is_online")
                       .prefetch_related(
            Prefetch(
                "assigned_to",
                # FIXME: что считать всё-таки сданным. Там где есть оценка?
                queryset=(StudentAssignment.objects
                          .select_related("student", "assignment")
                          .only("pk", "assignment_id", "grade",
                                "student_id", "first_submission_at",
                                "student__gender", "student__curriculum_year",
                                "assignment__course_offering_id",
                                "assignment__grade_max",
                                "assignment__grade_min",
                                "assignment__is_online")
                          .order_by())
            ))
                        # TODO: Сказать, что оставил только задания онлайн
                       .filter(course_offering_id=course_session_id,
                               )
                       .order_by("deadline_at"))

        serializer = AssignmentsStatsSerializer(assignments, many=True)
        return Response(serializer.data)


class EnrollmentsStats(APIView):
    """
    Aggregate stats about course offering assignment progress.
    """
    http_method_names = ['get']
    permission_classes = [CuratorAccessPermission]

    def get(self, request, course_session_id, format=None):
        enrollments = (Enrollment
                       .objects
                       .only("pk", "grade", "student_id", "student__gender",
                             "student__curriculum_year")
                       .select_related("student")
                       .filter(course_offering_id=course_session_id)
                       .order_by())

        serializer = EnrollmentsStatsSerializer(enrollments, many=True)
        return Response(serializer.data)


class StudentsDiplomasStats(APIView):
    http_method_names = ['get']

    def get(self, request, graduation_year, format=None):
        students = CSCUser.objects.students_info(
            filters={
                "groups__in": [CSCUser.group.GRADUATE_CENTER],
                "graduation_year": graduation_year,
            },
            exclude_grades=[GRADES.unsatisfactory, GRADES.not_graded]
        )
        unique_teachers = set()
        hours = 0
        enrollments_total = 0
        unique_projects = set()
        unique_courses = set()
        excellent_total = 0
        good_total = 0
        for s in students:
            for project in s.project_set.all():
                unique_projects.add(project)
            for enrollment in s.enrollments:
                enrollments_total += 1
                if enrollment.grade == GRADES.excellent:
                    excellent_total += 1
                elif enrollment.grade == GRADES.good:
                    good_total += 1
                unique_courses.add(enrollment.course_offering.course)
                hours += enrollment.course_offering.courseclass_set.count() * 1.5
                for teacher in enrollment.course_offering.teachers.all():
                    unique_teachers.add(teacher.pk)
        stats = {
            "total": len(students),
            "teachers_total": len(unique_teachers),
            "hours": int(hours),
            "courses": {
                "total": len(unique_courses),
                "enrollments": enrollments_total
            },
            "marks": {
                "good": good_total,
                "excellent": excellent_total
            },
            "projects_total": len(unique_projects)
        }
        return Response(stats)
