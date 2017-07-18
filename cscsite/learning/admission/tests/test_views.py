import pytest
from django.urls import reverse

from core.factories import CityFactory
from core.settings.base import DEFAULT_CITY_CODE
from learning.admission.factories import ApplicantFactory, InterviewFactory, \
    CampaignFactory, InterviewerFactory, CommentFactory
from learning.admission.models import Applicant, Interview
from users.factories import UserFactory


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
    # Autoupdate for applicant status works each time you set approval/approved
    # and applicant status not in final state
    interview.status = Interview.APPROVAL
    interview.save()
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_SCHEDULED


@pytest.mark.django_db
def test_autoupdate_applicant_status_deffered():
    applicant = ApplicantFactory(status=Applicant.INTERVIEW_TOBE_SCHEDULED)
    interview = InterviewFactory(applicant=applicant, status=Interview.APPROVED)
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_SCHEDULED
    interview.status = Interview.DEFERRED
    interview.save()
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_TOBE_SCHEDULED


@pytest.mark.django_db
def test_autoupdate_applicant_status_completed():
    """
    1. If all interviewers leave a comment, change interview status to
    `complete` status. Also, update applicant status if it's not already in
    final state.
    2. If interview took a place and we later remove absent interviewers,
    try to switch interview and applicant status to `complete` state.
    """
    # Default applicant status is nullable, so we can easily set `complete`
    interview = InterviewFactory(status=Interview.COMPLETED)
    assert interview.applicant.status == Applicant.INTERVIEW_COMPLETED
    interview.delete()
    # Check first event
    interviewer1, interviewer2 = InterviewerFactory.create_batch(2)
    interview = InterviewFactory(
        status=Interview.APPROVED,
        interviewers=[interviewer1, interviewer2])
    assert interview.applicant.status == Applicant.INTERVIEW_SCHEDULED
    CommentFactory.create(interview=interview, interviewer=interviewer1)
    interview.refresh_from_db()
    assert interview.status == Interview.APPROVED
    comment2 = CommentFactory.create(interview=interview,
                                     interviewer=interviewer2)
    interview.refresh_from_db()
    assert interview.status == Interview.COMPLETED
    # Now try to remove interviewer and check that status was changed.
    comment2.delete()
    interview.status = Interview.APPROVED
    interview.applicant.status = Applicant.INTERVIEW_SCHEDULED
    interview.applicant.save()
    # Interviewers update won't emit interview `post_save` signal, so
    # change it before `save` method called
    interview.interviewers = [interviewer1]
    interview.save()
    interview.refresh_from_db()
    assert interview.interviewers.count() == 1
    assert interview.status == Interview.COMPLETED


@pytest.mark.django_db
def test_autoupdate_applicant_status_completed():
    """Automatically switch applicant status if interview completed"""



@pytest.mark.django_db
def test_autoupdate_applicant_status_from_final():
    """Don't update applicant status if it already in final state"""
    applicant = ApplicantFactory(status=Applicant.ACCEPT)
    InterviewFactory(applicant=applicant, status=Interview.APPROVED)
    applicant.refresh_from_db()
    assert applicant.status == Applicant.ACCEPT


@pytest.mark.django_db
def test_interview_results_dispatch_view(curator, client):
    # Not enough permissions if you are not a curator
    city1, city2 = CityFactory.create_batch(2)
    curator.city = city1
    curator.save()
    user = UserFactory(is_staff=False, city=city1)
    client.login(user)
    url = reverse('admission_interview_results_dispatch')
    response = client.get(url, follow=True)
    redirect_url, status_code = response.redirect_chain[-1]
    assert status_code == 302
    assert 'login' in redirect_url
    # No active campaigns at this moment.
    client.login(curator)
    response = client.get(url, follow=True)
    # Redirect to default city
    redirect_url, status_code = response.redirect_chain[0]
    assert redirect_url == reverse("admission_interview_results_by_city",
                                   kwargs={"city_slug": DEFAULT_CITY_CODE})
    # And then to applicants list page
    redirect_url, status_code = response.redirect_chain[1]
    assert redirect_url == reverse("admission_applicants")
    # Create campaign, but not with curator default city value
    campaign1 = CampaignFactory.create(city=city2, current=False)
    response = client.get(url, follow=True)
    redirect_url, status_code = response.redirect_chain[1]
    assert redirect_url == reverse("admission_applicants")
    # Make it active
    campaign1.current = True
    campaign1.save()
    # Now curator should see this active campaign tab
    response = client.get(url, follow=True)
    redirect_url, status_code = response.redirect_chain[0]
    assert redirect_url == reverse("admission_interview_results_by_city",
                                   kwargs={"city_slug": city2.pk})
    # Create campaign for curator default city, but not active
    campaign2 = CampaignFactory.create(city=city1, current=False)
    response = client.get(url, follow=True)
    redirect_url, status_code = response.redirect_chain[0]
    assert redirect_url == reverse("admission_interview_results_by_city",
                                   kwargs={"city_slug": city2.pk})
    # Make it active
    campaign2.current = True
    campaign2.save()
    response = client.get(url, follow=True)
    redirect_url, status_code = response.redirect_chain[0]
    assert redirect_url == reverse("admission_interview_results_by_city",
                                   kwargs={"city_slug": city1.pk})
