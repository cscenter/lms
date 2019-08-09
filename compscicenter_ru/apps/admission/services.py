from datetime import datetime, timedelta
from operator import attrgetter
from typing import List

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from admission.constants import INVITATION_EXPIRED_IN_HOURS
from admission.models import InterviewStream, InterviewInvitation, \
    Applicant
from learning.roles import Roles
from users.models import User


def create_invitation(streams: List[InterviewStream], applicant: Applicant):
    """Create invitation and send email to applicant."""
    streams = list(streams)  # Queryset -> list
    first_stream = min(streams, key=attrgetter('date'))
    tz = first_stream.get_timezone()
    first_day_interview_naive = datetime.combine(first_stream.date,
                                                 datetime.min.time())
    first_day_interview = tz.localize(first_day_interview_naive)
    # Calculate deadline for invitation. It can't be later than 00:00
    # of the first interview day
    expired_in_hours = INVITATION_EXPIRED_IN_HOURS
    expired_at = timezone.now() + timedelta(hours=expired_in_hours)
    expired_at = min(expired_at, first_day_interview)
    invitation = InterviewInvitation(applicant=applicant,
                                     expired_at=expired_at)
    with transaction.atomic():
        invitation.save()
        invitation.streams.add(*streams)
        invitation.send_email()


def create_student_from_applicant(applicant):
    """
    Create new model or override existent with data from applicant form.
    """
    try:
        user = User.objects.get(email=applicant.email)
    except User.DoesNotExist:
        username = applicant.email.split("@", maxsplit=1)[0]
        if User.objects.filter(username=username).exists():
            username = User.generate_random_username(attempts=5)
        if not username:
            raise RuntimeError(
                "Всё плохо. Имя {} уже занято. Cлучайное имя сгенерировать "
                "не удалось".format(username))
        random_password = User.objects.make_random_password()
        user = User.objects.create_user(username=username,
                                        email=applicant.email,
                                        password=random_password)
    if applicant.status == Applicant.VOLUNTEER:
        user.add_group(Roles.VOLUNTEER)
    else:
        user.add_group(Roles.STUDENT)
    user.add_group(Roles.STUDENT, site_id=settings.CLUB_SITE_ID)
    # Migrate data from application form to user profile
    same_attrs = [
        "first_name",
        "patronymic",
        "phone"
    ]
    for attr_name in same_attrs:
        setattr(user, attr_name, getattr(applicant, attr_name))
    try:
        user.stepic_id = int(applicant.stepic_id)
    except (TypeError, ValueError):
        pass
    user.last_name = applicant.surname
    user.enrollment_year = user.curriculum_year = timezone.now().year
    # Looks like the same fields below
    user.yandex_id = applicant.yandex_id if applicant.yandex_id else ""
    # For github store part after github.com/
    if applicant.github_id:
        user.github_id = applicant.github_id.split("github.com/",
                                                   maxsplit=1)[-1]
    user.workplace = applicant.workplace if applicant.workplace else ""
    user.uni_year_at_enrollment = applicant.course
    user.branch = applicant.campaign.branch
    user.university = applicant.university.name
    user.save()
    return user
