import json
from collections import OrderedDict

from django.db.models import Q
from django.utils.timezone import now
from django.views import generic
from rest_framework.response import Response
from rest_framework.views import APIView

from admission.models import Campaign, Interview, Comment
from core.settings.base import CENTER_FOUNDATION_YEAR
from courses.models import Course, Semester
from courses.constants import SemesterTypes
from courses.utils import get_term_index
from core.utils import bucketize
from learning.settings import StudentStatuses, GradeTypes
from users.constants import Roles
from users.mixins import CuratorOnlyMixin
from users.models import User


class StatsIndexView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "stats/index.html"


class StatsLearningView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "stats/learning.html"

    def get_context_data(self, **kwargs):
        context = super(StatsLearningView, self).get_context_data(**kwargs)
        # Terms grouped by year
        term_start = get_term_index(CENTER_FOUNDATION_YEAR,
                                    SemesterTypes.AUTUMN)
        terms = (Semester.objects.only("pk", "type", "year")
                 .filter(index__gte=term_start)
                 .order_by("-index"))
        context["terms"] = bucketize(terms, key=lambda x: x.year)
        # TODO: Если прикрутить REST API, то можно эту логику перенести
        # на клиент и сразу не грузить весь список курсов
        # Courses grouped by term
        courses = (Course.objects
                   .filter(is_open=False)
                   .values("pk", "semester_id", "meta_course__name")
                   .order_by("-semester_id", "meta_course__name"))
        courses = bucketize(courses, key=lambda x: x["semester_id"])
        # Find selected course and term
        course_id = self.request.GET.get("course_session_id")
        try:
            course_id = int(course_id)
        except TypeError:
            max_term_id = max(courses.keys())
            course_id = courses[max_term_id][0]["pk"]
        term_id = None
        for group in courses.values():
            for co in group:
                if co["pk"] == course_id:
                    term_id = co["semester_id"]
                    break
        if not term_id:
            # Replace with appropriate error
            raise Exception("{}".format(course_id))

        context["courses"] = courses
        context["data"] = {
            "selected": {
                "term_id": term_id,
                "course_session_id": course_id,
            },
        }

        context["json_data"] = json.dumps({
            "courses": courses,
            "course_session_id": course_id,
        })
        return context


class StatsAdmissionView(CuratorOnlyMixin, generic.TemplateView):
    template_name = "stats/admission.html"

    def get_context_data(self, **kwargs):
        campaigns, selected_campaign_id = self.get_campaigns()
        branches, selected_branch = self.get_branches(campaigns,
                                                      selected_campaign_id)
        interviewers, selected_interviewer = self.get_interviewers()
        interviewer_stats = selected_interviewer and (Comment.objects
             .filter(interviewer_id=selected_interviewer)
             .select_related("interview",
                             "interview__applicant",
                             "interview__applicant__campaign",
                             "interview__applicant__campaign__branch",
                             "interview__applicant__user")
             .prefetch_related("interview__applicant__user__groups"))
        context = {
            "branches": branches,
            "campaigns": campaigns,
            "interviewers": interviewers,
            "data": {
                "selected": {
                    "branch": selected_branch,
                    "campaign_id": selected_campaign_id,
                    "interviewer_id": selected_interviewer
                },
                "interviewer_stats": interviewer_stats
            },
            "json_data": json.dumps({
                "campaigns": {b.id: [{"id": c.id, "year": c.year} for c in cs] for b, cs in campaigns.items()},
                "campaignId": selected_campaign_id,
                "branchId": selected_branch.pk
            })
        }
        return context

    def get_campaigns(self):
        campaigns = list(Campaign.objects
                         .select_related('branch')
                         .order_by("-year", "branch__site", "branch__order"))
        campaigns = bucketize(campaigns, key=lambda c: c.branch)
        # Find selected campaign
        campaign_id = self.request.GET.get("campaign")
        try:
            campaign_id = int(campaign_id)
        except TypeError:
            branch = next(iter(campaigns))
            campaign_id = campaigns[branch][0].id
        return campaigns, campaign_id

    @staticmethod
    def get_branches(campaigns, selected_campaign_id):
        branches = {}
        selected_branch = None
        for by_branch in campaigns.values():
            for campaign in by_branch:
                branches[campaign.branch.id] = campaign.branch
                if campaign.id == selected_campaign_id:
                    selected_branch = campaign.branch
                    break
        return branches, selected_branch

    def get_interviewers(self):
        selected_interviewer = self.request.GET.get("interviewer", '')
        try:
            selected_interviewer = int(selected_interviewer)
        except ValueError:
            selected_interviewer = ''
        interviewers = (Interview.interviewers.through.objects
                        .distinct("user__last_name", "user_id")
                        .order_by("user__last_name")
                        .select_related("user"))
        return interviewers, selected_interviewer


class StudentsDiplomasStats(APIView):
    http_method_names = ['get']

    def get(self, request, graduation_year, format=None):
        filters = (Q(group__role=Roles.GRADUATE) &
                   Q(graduate_profile__graduation_year=graduation_year))
        if graduation_year == now().year and self.request.user.is_curator:
            filters = filters | Q(status=StudentStatuses.WILL_GRADUATE)
        students = (User.objects
                    .student_progress(exclude_grades=[GradeTypes.UNSATISFACTORY,
                                                      GradeTypes.NOT_GRADED])
                    .filter(filters)
                    .order_by('last_name', 'first_name', 'pk')
                    .distinct('last_name', 'first_name', 'pk'))
        unique_teachers = set()
        hours = 0
        enrollments_total = 0
        unique_projects = set()
        unique_courses = set()
        excellent_total = 0
        good_total = 0
        for s in students:
            for ps in s.projects_progress:
                unique_projects.add(ps.project_id)
            for enrollment in s.enrollments_progress:
                enrollments_total += 1
                if enrollment.grade == GradeTypes.EXCELLENT:
                    excellent_total += 1
                elif enrollment.grade == GradeTypes.GOOD:
                    good_total += 1
                unique_courses.add(enrollment.course.meta_course)
                hours += enrollment.course.courseclass_set.count() * 1.5
                for teacher in enrollment.course.teachers.all():
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
