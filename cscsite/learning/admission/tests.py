# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

import pytest

from learning.admission.factories import ApplicantFactory, InterviewFactory
from learning.admission.models import Applicant, Interview


@pytest.mark.django_db
def test_autoupdate_applicant_status_canceled():
    applicant = ApplicantFactory(status=Applicant.INTERVIEW_TOBE_SCHEDULED)
    # Default interview status is `APPROVAL`
    interview = InterviewFactory(applicant=applicant)
    # applicant status must be updated to `scheduled`
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_SCHEDULED
    interview.status = Interview.CANCELED
    interview.save()
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_TOBE_SCHEDULED
    # Autoupdate works only when interview created
    interview.status = Interview.APPROVAL
    interview.save()
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_TOBE_SCHEDULED


@pytest.mark.django_db
def test_autoupdate_applicant_status_deffered():
    applicant = ApplicantFactory(status=Applicant.INTERVIEW_TOBE_SCHEDULED)
    interview = InterviewFactory(applicant=applicant, status=Interview.WAITING)
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_SCHEDULED
    interview.status = Interview.DEFERRED
    interview.save()
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_TOBE_SCHEDULED


@pytest.mark.django_db
def test_autoupdate_applicant_status_completed():
    """Do not automatically switch applicant status if interview completed"""
    applicant = ApplicantFactory(status=Applicant.INTERVIEW_TOBE_SCHEDULED)
    interview = InterviewFactory(applicant=applicant,
                                 status=Interview.COMPLETED)
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_TOBE_SCHEDULED


@pytest.mark.django_db
def test_autoupdate_applicant_status_from_final():
    """Don't update applicant status if it already in final state"""
    applicant = ApplicantFactory(status=Applicant.ACCEPT)
    InterviewFactory(applicant=applicant, status=Interview.WAITING)
    applicant.refresh_from_db()
    assert applicant.status == Applicant.ACCEPT


@pytest.mark.django_db
def test_autoupdate_applicant_status_from_multi():
    """
    Don't update applicant status if we deactivate interview, but still have
    active interviews.
    """
    applicant = ApplicantFactory(status=Applicant.INTERVIEW_TOBE_SCHEDULED)
    interview = InterviewFactory(applicant=applicant,
                                 status=Interview.WAITING)
    interview2 = InterviewFactory(applicant=applicant,
                                  status=Interview.COMPLETED)
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_SCHEDULED
    interview.status = Interview.DEFERRED
    interview.save()
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_SCHEDULED
    # Now no active interviews
    interview2.status = Interview.CANCELED
    interview2.save()
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_TOBE_SCHEDULED
