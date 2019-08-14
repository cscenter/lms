import factory
from factory.fuzzy import FuzzyInteger, FuzzyChoice

from courses.tests.factories import SemesterFactory
from learning.projects.forms import ReportReviewForm, PracticeCriteriaForm
from learning.projects.models import Project, ProjectStudent, Report, Review, \
    ReportingPeriod, PracticeCriteria
from core.tests.factories import BranchFactory
from users.tests.factories import UserFactory, StudentFactory


class ReportingPeriodFactory(factory.DjangoModelFactory):
    class Meta:
        model = ReportingPeriod

    label = factory.Sequence(lambda n: "Period label %03d" % n)
    term = factory.SubFactory(SemesterFactory)
    start_on = factory.Faker('past_date', start_date="-10d", tzinfo=None)
    end_on = factory.Faker('future_date', end_date="+10d", tzinfo=None)


class ProjectFactory(factory.DjangoModelFactory):
    class Meta:
        model = Project

    name = factory.Sequence(lambda n: "Test student project %03d" % n)
    description = factory.Sequence(lambda n: ("Test student project "
                                              "description %03d" % n))
    supervisor = factory.Sequence(lambda n: "Test supervisor %03d" % n)
    project_type = 'practice'
    semester = factory.SubFactory(SemesterFactory)
    branch = factory.SubFactory(BranchFactory)

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

    student = factory.SubFactory(StudentFactory)
    project = factory.SubFactory(ProjectFactory)
    supervisor_grade = FuzzyInteger(-15, 15)
    presentation_grade = FuzzyInteger(0, 10)


class ReportFactory(factory.DjangoModelFactory):
    class Meta:
        model = Report

    project_student = factory.SubFactory(ProjectStudentFactory)
    reporting_period = factory.SubFactory(ReportingPeriodFactory)
    score_activity = FuzzyChoice([v for v, _ in Report.ACTIVITY])
    score_quality = FuzzyChoice([v for v, _ in Report.QUALITY])


class ReviewFactory(factory.DjangoModelFactory):
    class Meta:
        model = Review

    report = factory.SubFactory(ReportFactory)
    reviewer = factory.SubFactory(UserFactory)

    @factory.post_generation
    def criteria(self, create, extracted, **kwargs):
        if not create:
            return
        if not extracted:
            criteria = ReviewPracticeCriteriaFactory(review=self)
            self.criteria = criteria


class ReviewPracticeCriteriaFactory(factory.DjangoModelFactory):
    class Meta:
        model = PracticeCriteria

    review = factory.SubFactory(ReviewFactory)
    score_global_issue = FuzzyChoice([v for v, _ in
                                      PracticeCriteria.GLOBAL_ISSUE_CRITERION])
    score_usefulness = FuzzyChoice([v for v, _ in
                                    PracticeCriteria.USEFULNESS_CRITERION])
    score_progress = FuzzyChoice([v for v, _ in PracticeCriteria.PROGRESS_CRITERION])
    score_problems = FuzzyChoice([v for v, _ in PracticeCriteria.PROBLEMS_CRITERION])
    score_technologies = FuzzyChoice([v for v, _ in
                                      PracticeCriteria.TECHNOLOGIES_CRITERION])
    score_plans = FuzzyChoice([v for v, _ in PracticeCriteria.PLANS_CRITERION])


def review_form_factory(is_completed=True):
    criteria = factory.build(dict, FACTORY_CLASS=ReviewPracticeCriteriaFactory,
                             review=None)
    del criteria["review"]
    data = {f"{PracticeCriteriaForm.prefix}-{k}": v for k, v in criteria.items()}

    data[f"{ReportReviewForm.prefix}-is_completed"] = is_completed
    return data
