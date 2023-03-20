import datetime

import pytest
import pytz

from admission.constants import InterviewSections
from admission.tests.factories import CampaignFactory, InterviewFactory
from admission.views import InterviewSerializer


@pytest.mark.django_db
def test_interview_serializer(rf):
    """Interview time zone depends on venue time zone"""
    tz_nsk = pytz.timezone("Asia/Novosibirsk")
    tz_msk = pytz.timezone("Europe/Moscow")
    campaign_nsk = CampaignFactory(branch__time_zone=tz_nsk)
    date_utc = datetime.datetime(2021, 1, 1, 8, 0, 0, 0, tzinfo=pytz.UTC)
    date_local = date_utc.astimezone(tz_nsk)
    interview = InterviewFactory(
        date=date_utc,
        section=InterviewSections.ALL_IN_ONE,
        applicant__campaign=campaign_nsk,
        venue__city__time_zone=tz_msk,
    )
    serializer = InterviewSerializer(interview, context={"request": rf.request()})
    assert serializer.data["time"] == "11:00"
