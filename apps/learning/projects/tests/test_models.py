# -*- coding: utf-8 -*-
import datetime
import math
import pytest

from courses.tests.factories import SemesterFactory
from learning.projects.constants import ProjectTypes
from learning.projects.tests.factories import ReportFactory, ReviewFactory, \
    ReportingPeriodFactory, ProjectStudentFactory
from learning.projects.models import REVIEW_SCORE_FIELDS, Review, \
    ReportingPeriod, ReportingPeriodKey
from learning.settings import Branches, GradeTypes
from learning.tests.factories import BranchFactory
from users.tests.factories import ProjectReviewerFactory


@pytest.mark.django_db
def test_final_reporting_periods_for_term():
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
    assert len(periods) == len(ProjectTypes.choices) * len(Branches.choices)
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
def test_final_reporting_periods_for_term_and_branch():
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
    assert len(periods) == len(ProjectTypes.choices) * len(Branches.choices)
    periods_spb = periods.for_branch(branch_spb)
    assert len(periods_spb) == len(ProjectTypes.choices)
    for project_type, _ in ProjectTypes.choices:
        key = ReportingPeriodKey(Branches.SPB, project_type)
        assert periods_spb[key] == rp_spb_all


@pytest.mark.django_db
def test_starting_periods():
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
    assert len(coming_periods) == len(ProjectTypes.choices) * len(Branches.choices)
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
    assert rp.score_to_grade(ps.total_score, ps.project) == GradeTypes.CREDIT
    ps.presentation_grade = 5
    assert ps.total_score == 6
    assert rp.score_to_grade(ps.total_score, ps.project) == GradeTypes.GOOD
    ps.project.is_external = True
    assert rp.score_to_grade(ps.total_score, ps.project) == GradeTypes.CREDIT


@pytest.mark.django_db
def test_mean_review_score():
    report = ReportFactory(score_quality=0, score_activity=0)
    project = report.project_student.project
    reviewer1, reviewer2 = ProjectReviewerFactory.create_batch(2)
    project.reviewers.add(reviewer1)
    project.reviewers.add(reviewer2)
    report.compute_fields("final_score")
    assert report.final_score == 0
    r1, r2 = ReviewFactory.create_batch(2, report=report)
    for field in REVIEW_SCORE_FIELDS:
        setattr(r1, field, 0)
        setattr(r2, field, 0)
    r1.save()
    r2.save()
    report.compute_fields("final_score")
    assert report.final_score == 0
    add = len(Review.PLANS_CRITERION) - 1
    r1.score_plans = add
    r1.save()
    report.compute_fields("final_score")
    assert report.final_score == math.ceil(add / 2)
    r2.score_plans = add
    r2.save()
    report.compute_fields("final_score")
    assert report.final_score == add
    report.score_activity += 1
    report.compute_fields("final_score")
    assert report.final_score == add + 1