import urllib

import pytest
import datetime

from bs4 import BeautifulSoup
from django.apps import apps
from django.urls import reverse
from django.utils import timezone, formats
from django.utils.timezone import now
from post_office.models import Email

from core.factories import CityFactory
from core.models import City
from core.settings.base import DEFAULT_CITY_CODE
from learning.admission.factories import ApplicantFactory, InterviewFactory, \
    CampaignFactory, InterviewerFactory, CommentFactory, \
    InterviewInvitationFactory, InterviewStreamFactory
from learning.admission.forms import InterviewFromStreamForm
from learning.admission.models import Applicant, Interview, InterviewInvitation
from users.factories import UserFactory

# TODO: если приняли приглашение и выбрали время - не создаётся для занятого слота. Создаётся напоминание (прочекать expired_at)
# TODO: Проверить время отправки напоминания, время/дату собеседования


@pytest.mark.django_db
def test_autoclose_application_form(client):
    today = timezone.now()
    campaign = CampaignFactory(year=today.year, current=True)
    url = reverse("admission:application_step", kwargs={"step": "welcome"})
    response = client.get(url)
    assert response.status_code == 200
    campaign.current = False
    campaign.save()
    response = client.get(url)
    assert response.status_code == 302
    assert "closed" in response.url
    campaign.current = True
    campaign.application_ends_at = today - datetime.timedelta(days=1)
    campaign.save()
    response = client.get(url)
    assert response.status_code == 302
    assert "closed" in response.url


@pytest.mark.django_db
def test_simple_interviews_list(client, curator, settings):
    settings.LANGUAGE_CODE = 'ru'
    client.login(curator)
    interviewer = InterviewerFactory()
    campaign = CampaignFactory(current=True)
    today = timezone.now()
    interview1, interview2, interview3 = InterviewFactory.create_batch(3,
        interviewers=[interviewer],
        date=today,
        status=Interview.COMPLETED,
        applicant__status=Applicant.INTERVIEW_COMPLETED,
        applicant__campaign=campaign)
    interview2.date = today + datetime.timedelta(days=1)
    interview2.save()
    interview3.date = today + datetime.timedelta(days=2)
    interview3.save()
    response = client.get(reverse('admission:interviews'))
    # For curator set default filters and redirect
    assert response.status_code == 302
    assert f"campaign={campaign.pk}" in response.url
    assert f"status={Interview.COMPLETED}" in response.url
    assert f"status={Interview.APPROVED}" in response.url
    today_date = formats.date_format(today, "SHORT_DATE_FORMAT")
    assert f"date_from={today_date}&date_to={today_date}" in response.url

    def format_url(campaign_id, date_from: str, date_to: str):
        return (reverse('admission:interviews') +
                f"?campaign={campaign_id}&status={Interview.COMPLETED}&"
                f"status={Interview.APPROVED}&"
                f"date_from={date_from}&date_to={date_to}")
    url = format_url(campaign.pk, today_date, today_date)
    response = client.get(url)
    assert response.status_code == 200
    assert "InterviewsCuratorFilter" in str(response.context['form'].__class__)
    assert len(response.context["interviews"]) == 1
    url = format_url(campaign.pk, today_date, "")
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.context["interviews"]) == 3
    url = format_url(campaign.pk,
                     today_date,
                     formats.date_format(interview2.date, "SHORT_DATE_FORMAT"))
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.context["interviews"]) == 2
    assert interview3 not in response.context["interviews"]


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
    city1, city2 = City.objects.all()[:2]
    curator.city = city1
    curator.save()
    user = UserFactory(is_staff=False, city=city1)
    client.login(user)
    url = reverse('admission:interview_results_dispatch')
    response = client.get(url, follow=True)
    redirect_url, status_code = response.redirect_chain[-1]
    assert status_code == 302
    assert 'login' in redirect_url
    # No active campaigns at this moment.
    client.login(curator)
    response = client.get(url, follow=True)
    # Redirect to default city
    redirect_url, status_code = response.redirect_chain[0]
    assert redirect_url == reverse("admission:interview_results_by_city",
                                   kwargs={"city_code": DEFAULT_CITY_CODE})
    # And then to applicants list page
    redirect_url, status_code = response.redirect_chain[1]
    assert redirect_url == reverse("admission:applicants")
    # Create campaign, but not with curator default city value
    campaign1 = CampaignFactory.create(city=city2, current=False)
    response = client.get(url, follow=True)
    redirect_url, status_code = response.redirect_chain[1]
    assert redirect_url == reverse("admission:applicants")
    # Make it active
    campaign1.current = True
    campaign1.save()
    # Now curator should see this active campaign tab
    response = client.get(url, follow=True)
    redirect_url, status_code = response.redirect_chain[0]
    assert redirect_url == reverse("admission:interview_results_by_city",
                                   kwargs={"city_code": city2.pk})
    # Create campaign for curator default city, but not active
    campaign2 = CampaignFactory.create(city=city1, current=False)
    response = client.get(url, follow=True)
    redirect_url, status_code = response.redirect_chain[0]
    assert redirect_url == reverse("admission:interview_results_by_city",
                                   kwargs={"city_code": city2.pk})
    # Make it active
    campaign2.current = True
    campaign2.save()
    response = client.get(url, follow=True)
    redirect_url, status_code = response.redirect_chain[0]
    assert redirect_url == reverse("admission:interview_results_by_city",
                                   kwargs={"city_code": city1.pk})


@pytest.mark.django_db
def test_interview_comment_create(curator, client, settings):
    interview = InterviewFactory.create()
    client.login(curator)
    form = {
        "text": "Comment message",
        "interview": interview.pk,
        "interviewer": curator.pk
    }
    url = reverse("admission:interview_comment", args=[interview.pk])
    response = client.post(url, form, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert response.status_code == 400  # invalid form: empty score
    form['score'] = 2
    response = client.post(url, form, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert response.status_code == 200


@pytest.mark.django_db
def test_invitation_slots(curator, client, settings):
    settings.LANGUAGE_CODE = 'ru'
    admission_settings = apps.get_app_config("admission")
    expired_after = admission_settings.INVITATION_EXPIRED_IN_HOURS
    # Make sure invitation will be active
    dt = timezone.now() + datetime.timedelta(hours=expired_after + 30)
    stream = InterviewStreamFactory(start_at=datetime.time(14, 0),
                                    end_at=datetime.time(15, 0),
                                    duration=20,
                                    date=dt.date(),
                                    with_assignments=False)
    assert stream.slots.count() == 3
    invitation = InterviewInvitationFactory(expired_at=dt, stream=stream)
    client.login(curator)
    response = client.get(invitation.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    assert any("14:40" in s.text for s in
               html.find_all('label', {"class": "btn"}))
    # 30 min diff if stream with assignments
    stream.with_assignments = True
    stream.save()
    response = client.get(invitation.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    assert any("13:30" in s.text for s in
               html.find_all('label', {"class": "btn"}))


@pytest.mark.django_db
def test_invitation_creation(curator, client, settings):
    settings.LANGUAGE_CODE = 'ru'
    applicant = ApplicantFactory(campaign__city_id='nsk')
    tomorrow = now() + datetime.timedelta(days=1)
    stream_nsk = InterviewStreamFactory(date=tomorrow.date(),
                                        with_assignments=False,
                                        venue__city_id='nsk')
    assert stream_nsk.slots.count() > 0
    client.login(curator)
    response = client.post(applicant.get_absolute_url(), {})
    assert response.status_code == 200
    assert len(response.context['form'].errors) > 0
    form_data = {
        InterviewFromStreamForm.prefix + "-stream": stream_nsk.pk
    }
    response = client.post(applicant.get_absolute_url(), form_data, follow=True)
    message = list(response.context['messages'])[0]
    assert 'success' in message.tags
    assert Email.objects.count() == 1
    invitation_qs = (Email.objects
                     .filter(template__name=InterviewInvitation.EMAIL_TEMPLATE))
    assert invitation_qs.count() == 1
    assert Interview.objects.count() == 0
    assert InterviewInvitation.objects.count() == 1


@pytest.mark.django_db
def test_interview_from_slot(curator, client, settings):
    settings.LANGUAGE_CODE = 'ru'
    admission_settings = apps.get_app_config("admission")
    expired_after = admission_settings.INVITATION_EXPIRED_IN_HOURS
    applicant = ApplicantFactory(campaign__city_id='nsk')
    tomorrow = now() + datetime.timedelta(days=1)
    interviewer = InterviewerFactory()
    stream_nsk = InterviewStreamFactory(date=tomorrow.date(),
                                        start_at=datetime.time(hour=12),
                                        end_at=datetime.time(hour=15),
                                        with_assignments=False,
                                        venue__city_id='nsk',
                                        interviewers=[interviewer])
    assert stream_nsk.slots.count() > 0
    # Make slot busy
    slot = stream_nsk.slots.order_by("start_at").first()
    interview = InterviewFactory()
    slot.interview_id = interview.pk
    slot.save()
    # Try to create interview from busy slot
    client.login(curator)
    form_data = {
        InterviewFromStreamForm.prefix + "-stream": stream_nsk.pk,
        InterviewFromStreamForm.prefix + "-slot": slot.pk
    }
    assert Interview.objects.count() == 1
    response = client.post(applicant.get_absolute_url(), form_data, follow=True)
    assert response.status_code == 200
    message = list(response.context['messages'])[0]
    assert 'error' in message.tags
    assert Interview.objects.count() == 1
    # Empty slot and repeat
    slot.interview_id = None
    slot.save()
    response = client.post(applicant.get_absolute_url(), form_data, follow=True)
    message = list(response.context['messages'])[0]
    assert 'success' in message.tags
    assert InterviewInvitation.objects.count() == 0
    assert Interview.objects.count() == 2
    # Check interview date
    interview = Interview.objects.get(applicant=applicant)
    assert interview.date.hour == 5  # UTC +7 for nsk
    assert interview.date_local().hour == slot.start_at.hour
    assert interview.date_local().minute == slot.start_at.minute
