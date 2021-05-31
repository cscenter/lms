from typing import List, Optional
from uuid import uuid4

from django.db.models import Q

from admission.constants import InterviewInvitationStatuses
from admission.models import InterviewInvitation, InterviewSlot


def get_occupied_slot(*, invitation: InterviewInvitation) -> Optional[InterviewSlot]:
    slot = (InterviewSlot.objects
            .filter(interview_id=invitation.interview_id,
                    interview__applicant_id=invitation.applicant_id)
            .select_related("stream__interview_format",
                            "interview__applicant__campaign")
            .first())
    # Interview could be reassigned to another applicant
    # after the slot was occupied
    if slot.interview.applicant_id != invitation.applicant_id:
        return None
    return slot


def get_interview_invitation(*, year: int, secret_code: uuid4,
                             filters: List[Q] = None) -> Optional[InterviewInvitation]:
    filters = filters or []
    try:
        return (InterviewInvitation.objects
                .filter(*filters,
                        secret_code=secret_code,
                        applicant__campaign__year=year)
                .select_related("applicant__campaign")
                .prefetch_related("streams")
                .get())
    except InterviewInvitation.DoesNotExist:
        return None


def get_active_interview_invitation(*, year: int, secret_code: uuid4) -> Optional[InterviewInvitation]:
    # FIXME: filter by expired_at
    filters = [Q(status=InterviewInvitationStatuses.CREATED)]
    return get_interview_invitation(year=year, secret_code=secret_code,
                                    filters=filters)
