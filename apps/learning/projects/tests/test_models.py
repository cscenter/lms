# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

import math
import pytest

from learning.projects.tests.factories import ReportFactory, ReviewFactory
from learning.projects.models import REVIEW_SCORE_FIELDS, Review
from users.tests.factories import ProjectReviewerFactory


@pytest.mark.django_db
def test_mean_review_score():
    report = ReportFactory(score_quality=0, score_activity=0)
    project = report.project_student.project
    reviewer1, reviewer2 = ProjectReviewerFactory.create_batch(2)
    project.reviewers.add(reviewer1)
    project.reviewers.add(reviewer2)
    report.calculate_mean_scores()
    assert report.calculate_final_score() == 0
    r1, r2 = ReviewFactory.create_batch(2, report=report)
    for field in REVIEW_SCORE_FIELDS:
        setattr(r1, field, 0)
        setattr(r2, field, 0)
    r1.save()
    r2.save()
    report.calculate_mean_scores()
    assert report.calculate_final_score() == 0
    add = len(Review.PLANS_CRITERION) - 1
    r1.score_plans = add
    r1.save()
    report.calculate_mean_scores()
    assert report.calculate_final_score() == math.ceil(add / 2)
    r2.score_plans = add
    r2.save()
    report.calculate_mean_scores()
    assert report.calculate_final_score() == add
    report.score_activity += 1
    assert report.calculate_final_score() == add + 1