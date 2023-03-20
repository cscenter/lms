import datetime
from uuid import uuid4

import pytest

from admission.constants import ContestTypes, InterviewSections
from admission.services import get_latest_contest_results_task
from admission.tests.factories import (
    CampaignFactory,
    InterviewInvitationFactory,
    InterviewSlotFactory,
)
from core.urls import reverse
from users.tests.factories import CuratorFactory, UserFactory


@pytest.mark.django_db
def test_appointment_create_interview(client):
    slot = InterviewSlotFactory(
        interview=None,
        stream__section=InterviewSections.MATH,
        start_at=datetime.time(14, 0),
        end_at=datetime.time(16, 0),
    )
    invitation = InterviewInvitationFactory(interview=None, streams=[slot.stream])
    # Use unknown secret code
    url = reverse(
        "appointment:api:interview_appointment_slots",
        kwargs={
            "year": invitation.applicant.campaign.year,
            "secret_code": uuid4().hex,
            "slot_id": slot.pk,
        },
    )
    response = client.post(url)
    assert response.status_code == 404
    # Send request to the valid url
    url = reverse(
        "appointment:api:interview_appointment_slots",
        kwargs={
            "year": invitation.applicant.campaign.year,
            "secret_code": invitation.secret_code.hex,
            "slot_id": slot.pk,
        },
    )
    response = client.post(url)
    assert response.status_code == 201
    # Repeat the same request
    response = client.post(url)
    assert response.status_code == 400
    assert "errors" in response.json()
    assert any(m["code"] == "accepted" for m in response.json()["errors"])


@pytest.mark.django_db
def test_campaign_create_contest_results_import_task(client):
    campaign = CampaignFactory(current=True)
    url = reverse(
        "admission:api:import_contest_scores",
        kwargs={"campaign_id": campaign.id, "contest_type": ContestTypes.TEST},
    )
    # Need any auth
    response = client.post(url)
    assert response.status_code == 401
    # No permissions
    client.login(UserFactory())
    response = client.post(url)
    assert response.status_code == 403
    # Validation Error
    client.login(CuratorFactory())
    wrong_contest_type = len(ContestTypes.values) + 1
    assert wrong_contest_type not in ContestTypes.values
    wrong_url = reverse(
        "admission:api:import_contest_scores",
        kwargs={"campaign_id": campaign.id, "contest_type": wrong_contest_type},
    )
    response = client.post(wrong_url)
    assert response.status_code == 400
    json_data = response.json()
    assert "errors" in json_data
    assert any(error["field"] == "contest_type" for error in json_data["errors"])
    # Correct case
    response = client.post(url)
    assert response.status_code == 201
    latest_task = get_latest_contest_results_task(campaign, ContestTypes.TEST)
    assert response.json()["id"] == latest_task.pk
    assert latest_task.is_completed
