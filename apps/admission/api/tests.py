import datetime
from uuid import uuid4

import pytest

from admission.constants import InterviewSections
from admission.tests.factories import InterviewInvitationFactory, InterviewSlotFactory
from core.urls import reverse


@pytest.mark.django_db
def test_appointment_create_interview(client):
    slot = InterviewSlotFactory(
        interview=None,
        stream__section=InterviewSections.MATH,
        start_at=datetime.time(14, 0),
        end_at=datetime.time(16, 0),
    )
    invitation = InterviewInvitationFactory(interview=None, streams=[slot.stream])
    url = reverse("appointment:api:interview_appointment_slots", kwargs={
        "year": invitation.applicant.campaign.year,
        "secret_code": uuid4().hex,
        "slot_id": slot.pk})
    response = client.post(url)
    assert response.status_code == 404
    url = reverse("appointment:api:interview_appointment_slots", kwargs={
            "year": invitation.applicant.campaign.year,
            "secret_code": invitation.secret_code.hex,
            "slot_id": slot.pk})
    response = client.post(url)
    assert response.status_code == 201
    # Repeat the same request
    response = client.post(url)
    assert response.status_code == 400
    assert 'errors' in response.json()
    assert any(m['code'] == "accepted" for m in response.json()['errors'])
