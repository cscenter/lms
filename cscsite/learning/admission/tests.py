# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

import pytest

from learning.admission.factories import ApplicantFactory, InterviewFactory
from learning.admission.models import Applicant, Interview


@pytest.mark.django_db
def test_autoupdate_applicant_status():
    applicant = ApplicantFactory(status=Applicant.INTERVIEW_TOBE_SCHEDULED)
    interview = InterviewFactory(applicant=applicant)
    # Change applicant status to `scheduled`
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_SCHEDULED
    interview.status = Interview.CANCELED
    interview.save()
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_TOBE_SCHEDULED
    # Do not automatically switch applicant status if interview completed
    interview.status = Interview.COMPLETED
    interview.save()
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_TOBE_SCHEDULED