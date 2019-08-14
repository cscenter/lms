import datetime

import pytest
from post_office.models import Email, STATUS as EMAIL_STATUS

from admission.constants import INTERVIEW_FEEDBACK_TEMPLATE, \
    INVITATION_EXPIRED_IN_HOURS
from admission.services import create_invitation
from admission.tests.factories import InterviewFactory, InterviewerFactory, \
    CommentFactory, InterviewStreamFactory, ApplicantFactory
from admission.models import Interview, InterviewInvitation
from learning.settings import Branches


@pytest.mark.django_db
def test_create_invitation(mocker):
    # Fix current time
    mocked_timezone = mocker.patch('django.utils.timezone.now')
    dt_utc = datetime.datetime(2018, month=3, day=8, hour=13, minute=0,
                               tzinfo=datetime.timezone.utc)
    mocked_timezone.return_value = dt_utc
    tomorrow = datetime.date(2018, month=3, day=9)
    from django.utils import timezone
    stream = InterviewStreamFactory(start_at=datetime.time(14, 0),
                                    end_at=datetime.time(16, 0),
                                    duration=20,
                                    date=tomorrow,
                                    with_assignments=False,
                                    campaign__current=True)
    applicant = ApplicantFactory(campaign=stream.campaign)
    tz = stream.venue.get_timezone()
    tomorrow_begin = datetime.datetime.combine(tomorrow,
                                               datetime.datetime.min.time())
    tomorrow_begin_local = tz.localize(tomorrow_begin)
    expired_at_expected = dt_utc + datetime.timedelta(hours=INVITATION_EXPIRED_IN_HOURS)
    assert expired_at_expected > tomorrow_begin_local
    create_invitation([stream], applicant)
    assert InterviewInvitation.objects.count() == 1
    invitation = InterviewInvitation.objects.first()
    expired_at_local = timezone.localtime(invitation.expired_at, timezone=tz)
    assert expired_at_local.strftime("%d.%m.%Y %H:%M") == "09.03.2018 00:00"


@pytest.mark.django_db
def test_generate_interview_feedback_email():
    email_qs = Email.objects.filter(template__name=INTERVIEW_FEEDBACK_TEMPLATE)
    interview = InterviewFactory(status=Interview.APPROVED,
                                 applicant__campaign__branch__code=Branches.SPB)
    assert Email.objects.count() == 0
    interview.status = Interview.COMPLETED
    interview.save()
    assert email_qs.count() == 1
    # Make sure feedback email is unique per interview
    interview.status = Interview.APPROVED
    interview.save()
    interview.status = Interview.COMPLETED
    interview.save()
    assert email_qs.count() == 1
    email = email_qs.first()
    assert email.status != EMAIL_STATUS.sent
    # Update email scheduled time if interview date was changed
    interview.date += datetime.timedelta(days=1)
    interview.save()
    interview_date = interview.date_local()
    new_scheduled_time = interview_date.replace(hour=21, minute=0, second=0,
                                                microsecond=0)
    email.refresh_from_db()
    assert email.scheduled_time == new_scheduled_time
    interviewer1, interviewer2 = InterviewerFactory.create_batch(2)
    interview.interviewers.add(interviewer1)
    interview.interviewers.add(interviewer2)
    # If last interviewer sent comment -> update interview status to `completed`
    # and generate feedback email
    Email.objects.all().delete()
    assert Email.objects.count() == 0
    interview.status = Interview.APPROVED
    interview.save()
    CommentFactory(interview=interview, interviewer=interviewer1)
    interview.refresh_from_db()
    assert interview.status != Interview.COMPLETED
    assert Email.objects.count() == 0
    CommentFactory(interview=interview, interviewer=interviewer2)
    interview.refresh_from_db()
    assert interview.status == Interview.COMPLETED
    assert Email.objects.count() == 1
