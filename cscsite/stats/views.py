import itertools
import json
from collections import OrderedDict

from django.db.models import Q
from django.utils.timezone import now

from django.views import generic
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.admission.models import Campaign
from learning.models import Semester, CourseOffering
from learning.settings import CENTER_FOUNDATION_YEAR, SEMESTER_TYPES, GRADES
from learning.utils import get_term_index

from learning.viewmixins import CuratorOnlyMixin
from users.models import CSCUser


class StatsIndexView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "stats/index.html"


class StatsLearningView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "stats/learning.html"

    def get_context_data(self, **kwargs):
        context = super(StatsLearningView, self).get_context_data(**kwargs)
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


class StatsAdmissionView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "stats/admission.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaigns = list(Campaign.objects
                         .values("pk", "year", "city_id", "city__name")
                         .order_by("city_id", "-year"))
        cities = OrderedDict()
        for c in campaigns:
            cities[c["city_id"]] = c["city__name"]
        campaigns = {city_code: list(cs) for city_code, cs in
                     itertools.groupby(campaigns, key=lambda c: c["city_id"])}
        # Find selected campaign and term
        campaign_id = self.request.GET.get("campaign")
        try:
            campaign_id = int(campaign_id)
        except TypeError:
            city_code = next(iter(campaigns))
            campaign_id = campaigns[city_code][0]["pk"]
        city_code = None
        for by_city in campaigns.values():
            for c in by_city:
                if c["pk"] == campaign_id:
                    city_code = c["city_id"]
                    break
        context["cities"] = cities
        context["campaigns"] = campaigns
        context["data"] = {
            "selected": {
                "city_code": city_code,
                "campaign_id": campaign_id,
            },
        }
        context["json_data"] = json.dumps({
            "campaigns": campaigns,
            "campaign": campaign_id,
        })
        return context


class StudentsDiplomasStats(APIView):
    http_method_names = ['get']

    def get(self, request, graduation_year, format=None):
        filters = (Q(groups__in=[CSCUser.group.GRADUATE_CENTER]) &
                   Q(graduation_year=graduation_year))
        if graduation_year == now().year and self.request.user.is_curator:
            filters = filters | Q(status=CSCUser.STATUS.will_graduate)
        students = CSCUser.objects.students_info(
            filters=filters,
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
            for ps in s.projects_through:
                unique_projects.add(ps.project_id)
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