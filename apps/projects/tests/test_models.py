import datetime
import math

import pytest

from core.models import Branch
from core.tests.factories import BranchFactory
from courses.tests.factories import SemesterFactory
from learning.settings import Branches
from projects.constants import ProjectGradeTypes, ProjectTypes
from projects.models import ReportingPeriod, ReportingPeriodKey
from projects.tests.factories import (
    ProjectReviewerFactory, ProjectStudentFactory, ReportFactory,
    ReportingPeriodFactory, ReviewFactory
)


@pytest.mark.django_db
def test_final_reporting_periods_for_term(settings):
    branch_nsk = BranchFactory(code=Branches.NSK)
    branch_spb = BranchFactory(code=Branches.SPB)
    current_term = SemesterFactory.create_current()
    prev_term = SemesterFactory.create_prev(current_term)
    start_on = current_term.starts_at.date()
    ReportingPeriodFactory(term=prev_term,
                           branch=branch_spb,
                           start_on=start_on,
                           end_on=start_on + datetime.timedelta(days=2),
                           score_excellent=10, score_good=6,
                           score_pass=3)
    periods = ReportingPeriod.get_final_periods(current_term)
    assert len(periods) == 0
    rp_spb_all = ReportingPeriodFactory(term=current_term,
                                        branch=branch_spb,
                                        start_on=start_on,
                                        end_on=start_on + datetime.timedelta(days=2),
                                        score_excellent=10, score_good=6,
                                        score_pass=3)
    rp_nsk_all = ReportingPeriodFactory(term=current_term,
                                        branch=branch_nsk,
                                        start_on=start_on,
                                        end_on=start_on + datetime.timedelta(days=2))
    periods = ReportingPeriod.get_final_periods(current_term)
    assert len(periods) == 2 * len(ProjectTypes.choices)
    for project_type, _ in ProjectTypes.choices:
        key = ReportingPeriodKey(Branches.SPB, project_type)
        assert periods[key] == rp_spb_all
    # Goes after `rp_spb_all`
    rp_spb_all2 = ReportingPeriodFactory(term=current_term,
                                         branch=branch_spb,
                                         start_on=start_on + datetime.timedelta(days=3),
                                         end_on=start_on + datetime.timedelta(days=4),
                                         score_excellent=20, score_good=12,
                                         score_pass=6)
    periods = ReportingPeriod.get_final_periods(current_term)
    assert len(periods) == 2 * len(ProjectTypes.choices)
    for project_type, _ in ProjectTypes.choices:
        key = ReportingPeriodKey(Branches.SPB, project_type)
        assert periods[key] == rp_spb_all2
    # Customize reporting period for research project types
    rp_spb_research = ReportingPeriodFactory(
        term=current_term, branch=branch_spb,
        project_type=ProjectTypes.research,
        start_on=start_on + datetime.timedelta(days=3),
        end_on=start_on + datetime.timedelta(days=4),
        score_excellent=7, score_good=6, score_pass=5)
    periods = ReportingPeriod.get_final_periods(current_term)
    assert len(periods) == 2 * len(ProjectTypes.choices)
    assert periods[ReportingPeriodKey(Branches.SPB, ProjectTypes.research)] == rp_spb_research
    assert periods[ReportingPeriodKey(Branches.SPB, ProjectTypes.practice)] == rp_spb_all2
    rp_all = ReportingPeriodFactory(term=current_term, branch=None,
                                    start_on=start_on,
                                    end_on=start_on + datetime.timedelta(days=2),
                                    score_excellent=100, score_good=50,
                                    score_pass=25)
    periods = ReportingPeriod.get_final_periods(current_term)
    assert len(periods) == len(ProjectTypes.choices) * len(Branch.objects.for_site(settings.SITE_ID))
    assert periods[ReportingPeriodKey(Branches.NSK, ProjectTypes.research)] == rp_nsk_all
    rp_nsk_all = ReportingPeriodFactory(
        term=current_term, branch=branch_nsk,
        start_on=start_on + datetime.timedelta(days=3),
        end_on=start_on + datetime.timedelta(days=5),
        score_excellent=77, score_good=66, score_pass=55)
    periods = ReportingPeriod.get_final_periods(current_term)
    assert periods[ReportingPeriodKey(Branches.NSK, ProjectTypes.research)] == rp_nsk_all
    assert periods[ReportingPeriodKey(Branches.NSK, ProjectTypes.practice)] == rp_nsk_all
    assert periods[ReportingPeriodKey(Branches.SPB, ProjectTypes.research)] == rp_spb_research
    assert periods[ReportingPeriodKey(Branches.SPB, ProjectTypes.practice)] == rp_spb_all2
    rp_nsk_latest_research = ReportingPeriodFactory(
        term=current_term, branch=branch_nsk,
        project_type=ProjectTypes.research,
        start_on=start_on + datetime.timedelta(days=6),
        end_on=start_on + datetime.timedelta(days=7),
        score_excellent=77, score_good=66, score_pass=55)
    periods = ReportingPeriod.get_final_periods(current_term)
    assert periods[ReportingPeriodKey(Branches.NSK, ProjectTypes.research)] == rp_nsk_latest_research
    assert periods[ReportingPeriodKey(Branches.NSK, ProjectTypes.practice)] == rp_nsk_all
    assert periods[ReportingPeriodKey(Branches.SPB, ProjectTypes.research)] == rp_spb_research
    assert periods[ReportingPeriodKey(Branches.SPB, ProjectTypes.practice)] == rp_spb_all2
    assert periods[ReportingPeriodKey(Branches.DISTANCE, ProjectTypes.practice)] == rp_all
    assert periods[ReportingPeriodKey(Branches.DISTANCE, ProjectTypes.research)] == rp_all


@pytest.mark.django_db
def test_final_reporting_periods_for_term_and_branch(settings):
    branch_nsk = BranchFactory(code=Branches.NSK)
    branch_spb = BranchFactory(code=Branches.SPB)
    current_term = SemesterFactory.create_current()
    start_on = current_term.starts_at.date()
    end_on = start_on + datetime.timedelta(days=2)
    rp_all = ReportingPeriodFactory(
        term=current_term,
        branch=None,
        start_on=start_on, end_on=end_on,
        score_excellent=10, score_good=6,
        score_pass=3)
    rp_spb_all = ReportingPeriodFactory(
        term=current_term,
        branch=branch_spb,
        start_on=start_on, end_on=end_on,
        score_excellent=10, score_good=6,
        score_pass=3)
    branch_spb = rp_spb_all.branch
    periods = ReportingPeriod.get_final_periods(current_term)
    assert len(periods) == len(ProjectTypes.choices) * len(Branch.objects.for_site(settings.SITE_ID))
    periods_spb = periods.for_branch(branch_spb)
    assert len(periods_spb) == len(ProjectTypes.choices)
    for project_type, _ in ProjectTypes.choices:
        key = ReportingPeriodKey(Branches.SPB, project_type)
        assert periods_spb[key] == rp_spb_all


@pytest.mark.django_db
def test_starting_periods(settings):
    branch_nsk = BranchFactory(code=Branches.NSK)
    branch_spb = BranchFactory(code=Branches.SPB)
    current_term = SemesterFactory.create_current()
    start_on = current_term.starts_at.date()
    end_on = start_on + datetime.timedelta(days=2)
    rp_all = ReportingPeriodFactory(
        term=current_term,
        branch=None,
        start_on=start_on, end_on=end_on,
        score_excellent=10, score_good=6,
        score_pass=3)
    rp_spb_all = ReportingPeriodFactory(
        term=current_term,
        branch=branch_spb,
        start_on=start_on, end_on=end_on,
        score_excellent=5, score_good=3,
        score_pass=1)
    rp_spb_all2 = ReportingPeriodFactory(
        term=current_term,
        branch=branch_spb,
        start_on=start_on + datetime.timedelta(days=2),
        end_on=end_on,
        score_excellent=50, score_good=30,
        score_pass=10)
    periods = ReportingPeriod.get_periods(start_on=start_on + datetime.timedelta(days=1))
    assert len(periods) == 0
    coming_periods = ReportingPeriod.get_periods(start_on=start_on)
    assert len(coming_periods) == len(ProjectTypes.choices) * len(Branch.objects.for_site(settings.SITE_ID))
    key = ReportingPeriodKey(Branches.NSK, ProjectTypes.research)
    assert coming_periods[key] == [rp_all]
    key = ReportingPeriodKey(Branches.SPB, ProjectTypes.research)
    assert coming_periods[key] == [rp_spb_all]
    coming_periods = ReportingPeriod.get_periods(start_on=start_on + datetime.timedelta(days=2))
    assert coming_periods[key] == [rp_spb_all2]
    rp_spb_research = ReportingPeriodFactory(
        term=current_term,
        branch=branch_spb,
        project_type=ProjectTypes.research,
        start_on=start_on + datetime.timedelta(days=2),
        end_on=end_on,
        score_excellent=50, score_good=30,
        score_pass=10)
    coming_periods = ReportingPeriod.get_periods(start_on=start_on + datetime.timedelta(days=2))
    assert coming_periods[key] == [rp_spb_research]


@pytest.mark.django_db
def test_ending_periods():
    current_term = SemesterFactory.create_current()
    start_on = current_term.starts_at.date()
    end_on = start_on + datetime.timedelta(days=5)
    branch_nsk = BranchFactory(code=Branches.NSK)
    branch_spb = BranchFactory(code=Branches.SPB)
    rp_nsk_all = ReportingPeriodFactory(
        term=current_term,
        branch=branch_nsk,
        start_on=start_on, end_on=end_on,
        score_excellent=10, score_good=6,
        score_pass=3)
    rp_spb_all = ReportingPeriodFactory(
        term=current_term,
        branch=branch_spb,
        start_on=start_on, end_on=end_on + datetime.timedelta(days=2),
        score_excellent=5, score_good=3,
        score_pass=1)
    ending_periods = ReportingPeriod.get_periods(end_on=end_on + datetime.timedelta(days=1))
    assert len(ending_periods) == 0
    ending_periods = ReportingPeriod.get_periods(end_on=end_on)
    assert len(ending_periods) == len(ProjectTypes.choices)
    for project_type, _ in ProjectTypes.choices:
        key = ReportingPeriodKey(Branches.NSK, project_type)
        assert ending_periods[key] == [rp_nsk_all]
    ending_periods = ReportingPeriod.get_periods(end_on=end_on, start_on__gt=start_on)
    assert len(ending_periods) == 0


@pytest.mark.django_db
def test_reporting_period_score_to_grade():
    current_term = SemesterFactory.create_current()
    start_on = current_term.starts_at.date()
    end_on = start_on + datetime.timedelta(days=2)
    rp = ReportingPeriodFactory(term=current_term,
                                start_on=start_on, end_on=end_on,
                                score_excellent=10, score_good=6,
                                score_pass=3)
    ps = ProjectStudentFactory(project__semester=current_term,
                               project__is_external=False,
                               supervisor_grade=1,
                               presentation_grade=2)
    assert ps.total_score == 3
    assert rp.score_to_grade(ps.total_score, ps.project) == ProjectGradeTypes.CREDIT
    ps.presentation_grade = 5
    assert ps.total_score == 6
    assert rp.score_to_grade(ps.total_score, ps.project) == ProjectGradeTypes.GOOD
    ps.project.is_external = True
    assert rp.score_to_grade(ps.total_score, ps.project) == ProjectGradeTypes.CREDIT


@pytest.mark.django_db
def test_report_final_score():
    report = ReportFactory(score_quality=0, score_activity=0)
    project = report.project_student.project
    reviewer1, reviewer2 = ProjectReviewerFactory.create_batch(2)
    project.reviewers.add(reviewer1)
    project.reviewers.add(reviewer2)
    report.compute_fields("final_score")
    assert report.final_score == 0
    review1, review2 = ReviewFactory.create_batch(2, report=report)
    for field in review1.criteria.SCORE_FIELDS:
        setattr(review1.criteria, field, 0)
    for field in review2.criteria.SCORE_FIELDS:
        setattr(review2.criteria, field, 0)
    review1.criteria.save()
    review2.criteria.save()
    report.compute_fields("final_score")
    assert report.final_score == 0
    score_planes_value = 2
    review1.criteria.score_plans = score_planes_value
    review1.criteria.save()
    report.compute_fields("final_score")
    # All reviews are not completed
    assert report.final_score == 0
    review1.is_completed = True
    review1.save()
    review2.is_completed = True
    review2.save()
    report.compute_fields("final_score")
    assert report.final_score == math.ceil(score_planes_value / 2)
    review2.criteria.score_plans = score_planes_value
    review2.criteria.save()
    report.compute_fields("final_score")
    assert report.final_score == score_planes_value
    score_activity_value = 1
    report.score_activity = score_activity_value
    report.compute_fields("final_score")
    assert report.final_score == score_planes_value + score_activity_value
