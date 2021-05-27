from typing import Optional
from uuid import uuid4

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


def get_interview_invitation(*, year: int, secret_code: uuid4) -> Optional[InterviewInvitation]:
    return (InterviewInvitation.objects
            .filter(secret_code=secret_code,
                    applicant__campaign__year=year)
            .select_related("applicant__campaign")
            .prefetch_related("streams")
            # FIXME: add unique constraint (year, secret_code)
            .first())
