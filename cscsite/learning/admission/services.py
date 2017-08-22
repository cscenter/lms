import datetime

from django.apps import apps
from django.db import transaction
from django.utils import timezone

from learning.admission.models import InterviewStream, InterviewInvitation, \
    Applicant

ADMISSION_SETTINGS = apps.get_app_config("admission")


def create_invitation(stream: InterviewStream, applicant: Applicant, **kwargs):
    """Create invitation and send email to applicant."""
    tz = stream.get_city_timezone()
    interview_day = datetime.datetime(stream.date.year, stream.date.month,
                                      stream.date.day, tzinfo=tz)
    # Calculate deadline for invitation
    expired_in_hours = ADMISSION_SETTINGS.INVITATION_EXPIRED_IN_HOURS
    expired_at = timezone.now() + datetime.timedelta(hours=expired_in_hours)
    # Deadline is 00:00 of the interview day
    expired_at = min(expired_at, interview_day)
    invitation = InterviewInvitation(applicant=applicant,
                                     date=stream.date,
                                     expired_at=expired_at,
                                     stream=stream)
    with transaction.atomic():
        invitation.save()
        invitation.send_email(kwargs.get('uri_builder'))
