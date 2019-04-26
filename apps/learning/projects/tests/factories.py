import factory
from django.forms import model_to_dict
from factory.fuzzy import FuzzyInteger, FuzzyChoice

from core.urls import reverse
from courses.tests.factories import SemesterFactory
from learning.projects.forms import ReportReviewForm
from learning.projects.models import Project, ProjectStudent, Report, Review, \
    ReportingPeriod
from learning.tests.factories import BranchFactory
from users.tests.factories import UserFactory


class ReportingPeriodFactory(factory.DjangoModelFactory):
    class Meta:
        model = ReportingPeriod

    label = factory.Sequence(lambda n: "Period label %03d" % n)
    term = factory.SubFactory(SemesterFactory)
    branch = factory.SubFactory(BranchFactory)


class ProjectFactory(factory.DjangoModelFactory):
    class Meta:
        model = Project

    name = factory.Sequence(lambda n: "Test student project %03d" % n)
    description = factory.Sequence(lambda n: ("Test student project "
                                              "description %03d" % n))
    supervisor = factory.Sequence(lambda n: "Test supervisor %03d" % n)
    project_type = 'practice'
    semester = factory.SubFactory(SemesterFactory)

    @factory.post_generation
    def students(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for student in extracted:
                ProjectStudentFactory(student=student, project=self)

    @factory.post_generation
    def reviewers(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for reviewer in extracted:
                self.reviewers.add(reviewer)


class ProjectStudentFactory(factory.DjangoModelFactory):
    class Meta:
        model = ProjectStudent

    student = factory.SubFactory(UserFactory)
    project = factory.SubFactory(ProjectFactory)
    supervisor_grade = FuzzyInteger(-15, 15)
    presentation_grade = FuzzyInteger(0, 10)


class ReportFactory(factory.DjangoModelFactory):
    class Meta:
        model = Report

    project_student = factory.SubFactory(ProjectStudentFactory)
    score_activity = FuzzyChoice([v for v, _ in Report.ACTIVITY])
    score_quality = FuzzyChoice([v for v, _ in Report.QUALITY])


class ReviewFactory(factory.DjangoModelFactory):
    class Meta:
        model = Review

    report = factory.SubFactory(ReportFactory)
    reviewer = factory.SubFactory(UserFactory)
    score_global_issue = FuzzyChoice([v for v, _ in
                                      Review.GLOBAL_ISSUE_CRITERION])
    score_usefulness = FuzzyChoice([v for v, _ in
                                    Review.USEFULNESS_CRITERION])
    score_progress = FuzzyChoice([v for v, _ in Review.PROGRESS_CRITERION])
    score_problems = FuzzyChoice([v for v, _ in Review.PROBLEMS_CRITERION])
    score_technologies = FuzzyChoice([v for v, _ in
                                      Review.TECHNOLOGIES_CRITERION])
    score_plans = FuzzyChoice([v for v, _ in Review.PLANS_CRITERION])


class ReportReviewFormFactory:
    def __init__(self, *args, report, reviewer, **kwargs):
        new_review = ReviewFactory.build(report=report, reviewer=reviewer,
                                         **kwargs)
        form_data = {k:v for k, v in model_to_dict(new_review).items() if v is not None}
        form = ReportReviewForm(data=form_data)
        data = form.data
        # FIXME: Check if I can pass it directly to ReportReviewForm
        data[ReportReviewForm.prefix] = "1"
        self.data = data
        self.send_to = reverse("projects:project_report", kwargs={
            "student_pk": report.project_student.student.pk,
            "project_pk": report.project_student.project.pk,
        })

