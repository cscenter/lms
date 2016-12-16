import json

import itertools
from collections import OrderedDict

from django.core.urlresolvers import reverse
from django.db.models import Prefetch
from django.views import generic
from rest_framework.views import APIView
from rest_framework.response import Response

from api.permissions import CuratorAccessPermission
from learning.models import Course, Semester, CourseOffering, StudentAssignment, \
    Assignment
from learning.settings import CENTER_FOUNDATION_YEAR, SEMESTER_TYPES
from learning.utils import get_term_index
from learning.viewmixins import CuratorOnlyMixin
from stats.serializers import ParticipantsStatsSerializer, \
    AssignmentsStatsSerializer
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
        terms = OrderedDict()
        first_term = None
        for group_name, group in terms_grouped:
            group = list(group)
            if group:
                first_term = first_term or group[0]
            terms[group_name] = group
        context["terms"] = terms
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
            course_session_id = courses[first_term.pk][0]["pk"]
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
                               is_online=True)
                       .order_by("created"))

        serializer = AssignmentsStatsSerializer(assignments, many=True)
        return Response(serializer.data)
