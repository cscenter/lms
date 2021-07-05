import datetime

import pytest
from bs4 import BeautifulSoup
from post_office.models import Email

from django.utils import formats, timezone
from django.utils.timezone import now

from admission.constants import (
    INVITATION_EXPIRED_IN_HOURS, InterviewFormats, InterviewSections
)
from admission.forms import InterviewFromStreamForm
from admission.models import Applicant, Interview, InterviewInvitation
from admission.services import get_meeting_time
from admission.tests.factories import (
    ApplicantFactory, CampaignFactory, CommentFactory, InterviewerFactory,
    InterviewFactory, InterviewFormatFactory, InterviewInvitationFactory,
    InterviewStreamFactory
)
from admission.views import InterviewInvitationCreateView
from core.models import Branch
from core.tests.factories import BranchFactory
from core.timezone import now_local
from core.urls import reverse
from learning.settings import Branches
from users.tests.factories import CuratorFactory, UserFactory

# TODO: если приняли приглашение и выбрали время - не создаётся для занятого слота. Создаётся напоминание (прочекать expired_at)
# TODO: Проверить время отправки напоминания, время/дату собеседования


@pytest.mark.django_db
def test_simple_interviews_list(client, curator, settings):
    settings.LANGUAGE_CODE = 'ru'
    curator.branch = Branch.objects.get(code=Branches.NSK,
                                        site_id=settings.SITE_ID)
    curator.save()
    client.login(curator)
    interviewer = InterviewerFactory()
    branch_nsk = Branch.objects.get(code=Branches.NSK, site_id=settings.SITE_ID)
    campaign = CampaignFactory(current=True, branch=branch_nsk)
    today_local_nsk = now_local(branch_nsk.get_timezone())
    today_local_nsk_date = formats.date_format(today_local_nsk,
                                               "SHORT_DATE_FORMAT")
    interview1, interview2, interview3 = InterviewFactory.create_batch(3,
        interviewers=[interviewer],
        date=today_local_nsk,
        section=InterviewSections.ALL_IN_ONE,
        status=Interview.COMPLETED,
        applicant__status=Applicant.INTERVIEW_COMPLETED,
        applicant__campaign=campaign)
    interview2.date = today_local_nsk + datetime.timedelta(days=1)
    interview2.save()
    interview3.date = today_local_nsk + datetime.timedelta(days=2)
    interview3.save()
    response = client.get(reverse('admission:interviews:list'))
    # For curator set default filters and redirect
    assert response.status_code == 302
    assert f"campaign={campaign.pk}" in response.url
    assert f"status={Interview.COMPLETED}" in response.url
    assert f"status={Interview.APPROVED}" in response.url
    assert f"date_from={today_local_nsk_date}" in response.url
    assert f"date_to={today_local_nsk_date}" in response.url

    def format_url(campaign_id, date_from: str, date_to: str):
        return (reverse('admission:interviews:list') +
                f"?campaign={campaign_id}&status={Interview.COMPLETED}&"
                f"status={Interview.APPROVED}&"
                f"date_from={date_from}&date_to={date_to}")

    url = format_url(campaign.pk, today_local_nsk_date, today_local_nsk_date)
    response = client.get(url)
    assert response.status_code == 200
    assert "InterviewsCuratorFilter" in str(response.context['form'].__class__)
    assert len(response.context["interviews"]) == 1
    url = format_url(campaign.pk, today_local_nsk_date, "")
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.context["interviews"]) == 3
    url = format_url(campaign.pk,
                     today_local_nsk_date,
                     formats.date_format(interview2.date, "SHORT_DATE_FORMAT"))
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.context["interviews"]) == 2
    assert interview3 not in response.context["interviews"]

    # Checking the display of the venue in the interview table
    soup = BeautifulSoup(response.content, "html.parser")
    assert soup.find(id="venue") is not None

    # Checking filtering for curator their interviews
    url = format_url(campaign.pk, today_local_nsk_date, "") + f"&my_interviews=1"
    response = client.get(url)
    assert len(response.context["interviews"]) == 0

@pytest.mark.django_db
def test_interview_invitations_create_view(client, settings):
    curator = CuratorFactory()
    client.login(curator)
    base_url = reverse('admission:interviews:invitations:send')
    campaign = CampaignFactory(current=True, branch=BranchFactory(code=Branches.SPB))
    applicant = ApplicantFactory(status=Applicant.INTERVIEW_TOBE_SCHEDULED, campaign=campaign)
    applicant_2 = ApplicantFactory(status=Applicant.INTERVIEW_TOBE_SCHEDULED, campaign=campaign)
    applicant_3 = ApplicantFactory(status=Applicant.INTERVIEW_SCHEDULED, campaign=campaign)
    applicant_4 = ApplicantFactory(status=Applicant.INTERVIEW_TOBE_SCHEDULED, campaign=campaign)
    stream_all_in_one = InterviewStreamFactory(campaign=campaign, section=InterviewSections.ALL_IN_ONE)
    stream_math = InterviewStreamFactory(campaign=campaign, section=InterviewSections.MATH)
    interview_all_in_one = InterviewFactory(applicant=applicant_2, section=InterviewSections.ALL_IN_ONE)
    interview_math = InterviewFactory(applicant=applicant_4, section=InterviewSections.MATH)
    # Filter applicants by common section
    url_all_in_one = f"{base_url}?campaign={campaign.id}&section={InterviewSections.ALL_IN_ONE}"
    response = client.get(url_all_in_one)
    soup = BeautifulSoup(response.content, "html.parser")
    assert soup.find(text=applicant.full_name) is not None
    assert soup.find(text=applicant_2.full_name) is None
    assert soup.find(text=applicant_3.full_name) is None
    assert soup.find(text=applicant_4.full_name) is not None
    assert soup.find(text=stream_all_in_one) is not None
    assert soup.find(text=stream_math) is None
    # Filter applicants by InterviewSections.MATH section
    url_math = f"{base_url}?campaign={campaign.id}&section={InterviewSections.MATH}"
    response = client.get(url_math)
    soup = BeautifulSoup(response.content, "html.parser")
    assert soup.find(text=applicant.full_name) is not None
    assert soup.find(text=applicant_2.full_name) is None
    assert soup.find(text=applicant_3.full_name) is None
    assert soup.find(text=applicant_4.full_name) is None
    assert soup.find(text=stream_all_in_one) is None
    assert soup.find(text=stream_math) is not None


@pytest.mark.django_db
def test_autoupdate_applicant_status_canceled():
    applicant = ApplicantFactory(status=Applicant.INTERVIEW_TOBE_SCHEDULED)
    # Default interview status is `APPROVAL`
    interview = InterviewFactory(applicant=applicant, section=InterviewSections.ALL_IN_ONE)
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
def test_auto_update_applicant_status_deferred():
    applicant = ApplicantFactory(status=Applicant.INTERVIEW_TOBE_SCHEDULED)
    interview = InterviewFactory(applicant=applicant, status=Interview.APPROVED,
                                 section=InterviewSections.ALL_IN_ONE)
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_SCHEDULED
    interview.status = Interview.DEFERRED
    interview.save()
    applicant.refresh_from_db()
    assert applicant.status == Applicant.INTERVIEW_TOBE_SCHEDULED


@pytest.mark.django_db
def test_autocomplete_interview():
    """
    If all interviewers have left comments, change interview
    status to `complete`.
    """
    interviewer1, interviewer2, interviewer3 = InterviewerFactory.create_batch(3)
    interview = InterviewFactory(status=Interview.APPROVED,
                                 section=InterviewSections.ALL_IN_ONE,
                                 interviewers=[interviewer1, interviewer2])
    assert interview.applicant.status == Applicant.INTERVIEW_SCHEDULED
    CommentFactory(interview=interview, interviewer=interviewer1)
    interview.refresh_from_db()
    assert interview.status == Interview.APPROVED
    # Leave a comment from "curator"
    CommentFactory(interview=interview, interviewer=interviewer3)
    interview.refresh_from_db()
    assert interview.status == Interview.APPROVED
    CommentFactory(interview=interview, interviewer=interviewer2)
    interview.refresh_from_db()
    assert interview.status == Interview.COMPLETED
    # No assigned interviewers
    interview2 = InterviewFactory(status=Interview.APPROVED,
                                  section=InterviewSections.ALL_IN_ONE)
    CommentFactory(interview=interview2, interviewer=interviewer1)
    interview2.refresh_from_db()
    assert interview2.status == Interview.COMPLETED


@pytest.mark.django_db
def test_update_applicant_status_if_interview_has_been_completed():
    interview2 = InterviewFactory(status=Interview.APPROVED,
                                  section=InterviewSections.ALL_IN_ONE)
    CommentFactory(interview=interview2)
    interview2.refresh_from_db()
    assert interview2.status == Interview.COMPLETED
    assert interview2.applicant.status == Applicant.INTERVIEW_COMPLETED


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
    interview = InterviewFactory(status=Interview.COMPLETED,
                                 section=InterviewSections.ALL_IN_ONE)
    assert interview.applicant.status == Applicant.INTERVIEW_COMPLETED
    interview.delete()
    interviewer1, interviewer2 = InterviewerFactory.create_batch(2)
    interview = InterviewFactory(status=Interview.APPROVED,
                                 section=InterviewSections.ALL_IN_ONE,
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
    interview.save()
    interview.applicant.status = Applicant.INTERVIEW_SCHEDULED
    interview.applicant.save()
    interview.interviewers.clear()
    interview.interviewers.add(interviewer1)
    assert interview.interviewers.count() == 1
    interview.refresh_from_db()
    # FIXME: Removing interviewer won't emit interview post_save signal
    # assert interview.status == Interview.COMPLETED


@pytest.mark.django_db
def test_autoupdate_applicant_status_from_final():
    """Don't update applicant status if it already in final state"""
    applicant = ApplicantFactory(status=Applicant.ACCEPT)
    InterviewFactory(applicant=applicant, status=Interview.APPROVED,
                     section=InterviewSections.ALL_IN_ONE)
    applicant.refresh_from_db()
    assert applicant.status == Applicant.ACCEPT


@pytest.mark.django_db
def test_interview_results_dispatch_view(client, settings, assert_redirect,
                                         assert_login_redirect):
    # Not enough permissions if you are not a curator
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    branch_default = BranchFactory(code=settings.DEFAULT_BRANCH_CODE)
    user = UserFactory(is_staff=False, branch=branch_spb)
    client.login(user)
    url = reverse('admission:results:dispatch')
    response = client.get(url, follow=True)
    redirect_url, status_code = response.redirect_chain[-1]
    assert status_code == 302
    assert_login_redirect(url)
    # No active campaigns at this moment
    curator = CuratorFactory(branch=branch_spb)
    client.login(curator)
    response = client.get(url, follow=True)
    redirect_url, status_code = response.redirect_chain[0]
    assert redirect_url == reverse("admission:results:list",
                                   kwargs={"branch_code": branch_default.code})
    # And then to the applicants list page
    redirect_url, status_code = response.redirect_chain[1]
    assert redirect_url == reverse("admission:applicants:list")
    # Add inactive campaign
    campaign_nsk = CampaignFactory.create(branch=branch_nsk, current=False)
    response = client.get(url, follow=True)
    redirect_url, status_code = response.redirect_chain[1]
    assert redirect_url == reverse("admission:applicants:list")
    # Test redirection to the first active campaign
    campaign_nsk.current = True
    campaign_nsk.save()
    results_nsk = reverse("admission:results:list",
                          kwargs={"branch_code": branch_nsk.code})
    response = client.get(url)
    assert_redirect(response, results_nsk)
    # Create inactive campaign from the curator branch
    campaign_spb = CampaignFactory(branch=branch_spb, current=False)
    assert_redirect(client.get(url), results_nsk)
    # Then activate
    campaign_spb.order = 200
    campaign_spb.save()
    campaign_nsk.order = 100
    campaign_nsk.save()
    campaign_spb.current = True
    campaign_spb.save()
    results_spb = reverse("admission:results:list",
                          kwargs={"branch_code": branch_spb.code})
    assert_redirect(client.get(url), results_spb)


@pytest.mark.django_db
def test_interview_comment_create(curator, client, settings):
    interview = InterviewFactory(section=InterviewSections.ALL_IN_ONE)
    client.login(curator)
    form = {
        "text": "Comment message",
        "interview": interview.pk,
        "interviewer": curator.pk
    }
    url = reverse("admission:interviews:comment", args=[interview.pk])
    response = client.post(url, form, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert response.status_code == 400  # invalid form: empty score
    form['score'] = 2
    response = client.post(url, form, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert response.status_code == 200


@pytest.mark.django_db
def test_create_invitation(curator, client, settings):
    """Create invitation from single stream"""
    settings.LANGUAGE_CODE = 'ru'
    campaign = CampaignFactory()
    applicant = ApplicantFactory(campaign=campaign)
    tomorrow = now() + datetime.timedelta(days=2)
    InterviewStreamFactory(date=tomorrow.date(),
                           with_assignments=True,
                           campaign=campaign)
    stream = InterviewStreamFactory(date=tomorrow.date(),
                                    with_assignments=False,
                                    campaign=campaign)
    assert stream.slots.count() > 0
    client.login(curator)
    response = client.post(applicant.get_absolute_url(), {})
    assert response.status_code == 200
    assert len(response.context['form'].errors) > 0
    form_data = {
        InterviewFromStreamForm.prefix + "-streams": stream.pk
    }
    response = client.post(applicant.get_absolute_url(), form_data, follow=True)
    message = list(response.context['messages'])[0]
    assert 'success' in message.tags
    assert Email.objects.count() == 1
    assert Interview.objects.count() == 0
    assert InterviewInvitation.objects.count() == 1


@pytest.mark.django_db
def test_create_interview_from_slot(curator, client, settings):
    settings.LANGUAGE_CODE = 'ru'
    campaign = CampaignFactory(branch__code=Branches.NSK)
    applicant = ApplicantFactory(campaign=campaign)
    tomorrow_utc = now() + datetime.timedelta(days=2)
    interviewer = InterviewerFactory()
    stream = InterviewStreamFactory(date=tomorrow_utc.date(),
                                    section=InterviewSections.ALL_IN_ONE,
                                    start_at=datetime.time(hour=12),
                                    end_at=datetime.time(hour=15),
                                    campaign=campaign,
                                    with_assignments=False,
                                    interviewers=[interviewer])
    assert stream.slots.count() > 0
    # Make slot busy
    slot = stream.slots.order_by("start_at").first()
    interview = InterviewFactory(section=InterviewSections.ALL_IN_ONE)
    slot.interview_id = interview.pk
    slot.save()
    # Try to create interview for reserved slot
    assert Interview.objects.count() == 1
    client.login(curator)
    form_data = {
        InterviewFromStreamForm.prefix + "-streams": stream.pk,
        InterviewFromStreamForm.prefix + "-slot": slot.pk
    }
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


@pytest.mark.django_db
def test_create_student_from_applicant(client, curator, assert_redirect):
    applicant = ApplicantFactory()
    client.login(curator)
    assert not applicant.user_id
    response = client.post(reverse("admission:applicants:create_student",
                                   kwargs={"pk": applicant.pk}))
    assert response.status_code == 302
    applicant.refresh_from_db()
    assert applicant.user_id
    admin_url = reverse("admin:users_user_change", args=[applicant.user_id])
    assert_redirect(response, admin_url)
    # Student who was expelled in the first semester still could reapply
    # on general terms
    applicant_reapplied = ApplicantFactory(email=applicant.email)
    response = client.post(reverse("admission:applicants:create_student",
                                   kwargs={"pk": applicant_reapplied.pk}))
    assert response.status_code == 302
    applicant_reapplied.refresh_from_db()
    assert applicant_reapplied.user_id == applicant.user_id
    assert_redirect(response, admin_url)
