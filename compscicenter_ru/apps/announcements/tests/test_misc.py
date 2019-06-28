import datetime

import pytest

from announcements.models import Announcement
from announcements.tests.factories import AnnouncementTagFactory, \
    AnnouncementFactory


@pytest.mark.django_db
def test_announcement_manager(mocker):
    mocked_timezone = mocker.patch('django.utils.timezone.now')
    today_fixed = datetime.datetime(2019, month=3, day=8, hour=13, minute=0,
                                    tzinfo=datetime.timezone.utc)
    mocked_timezone.return_value = today_fixed
    tags = AnnouncementTagFactory.create_batch(2)
    yesterday = today_fixed - datetime.timedelta(days=2)
    tomorrow = today_fixed + datetime.timedelta(days=1)
    announcement = AnnouncementFactory(publish_start_at=yesterday,
                                       publish_end_at=yesterday,
                                       tags=tags)
    assert Announcement.current.count() == 0
    announcement = AnnouncementFactory(publish_end_at=tomorrow)
    assert Announcement.current.count() == 1
