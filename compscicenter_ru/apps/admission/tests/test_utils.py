import datetime

import pytest
from post_office.models import Email, STATUS as EMAIL_STATUS

from admission.constants import INTERVIEW_FEEDBACK_TEMPLATE
from admission.tests.factories import InterviewFactory, InterviewerFactory, \
    CommentFactory
from admission.models import Interview


@pytest.mark.django_db
def test_generate_interview_feedback_email():
    email_qs = Email.objects.filter(template__name=INTERVIEW_FEEDBACK_TEMPLATE)
    interview = InterviewFactory(status=Interview.APPROVED,
                                 applicant__campaign__city_id='spb')
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
