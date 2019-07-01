import datetime

import pytest
from bs4 import BeautifulSoup

from announcements.tests.factories import AnnouncementEventDetailsFactory


@pytest.mark.django_db
def test_announcement_dates_macros(client, settings):
    settings.LANGUAGE_CODE = 'ru'
    announcement_details = AnnouncementEventDetailsFactory()
    announcement = announcement_details.announcement
    response = client.get(announcement.get_absolute_url())
    assert response.status_code == 200
    announcement_details.starts_on = datetime.date(year=2019, month=7, day=1)
    announcement_details.starts_at = datetime.time(hour=13, minute=7)
    announcement_details.ends_on = None
    announcement_details.ends_at = None
    announcement_details.save()
    response = client.get(announcement.get_absolute_url())
    assert response.status_code == 200
    html = BeautifulSoup(response.content, "html.parser")
    event_details = html.find_all('div', {"class": "announcement__detail"})
    assert event_details
    assert any(t.find('span', text="1 июля 2019 13:07") for t in event_details)
    announcement_details.ends_on = datetime.date(year=2019, month=7, day=1)
    announcement_details.ends_at = datetime.time(hour=15, minute=7)
    announcement_details.save()
    response = client.get(announcement.get_absolute_url())
    assert response.status_code == 200
    html = BeautifulSoup(response.content, "html.parser")
    event_details = html.find_all('div', {"class": "announcement__detail"})
    assert event_details
    assert any(t.find('span', text="1 июля 2019 13:07 — 15:07") for t in event_details)
    announcement_details.ends_on = datetime.date(year=2019, month=7, day=3)
    announcement_details.save()
    response = client.get(announcement.get_absolute_url())
    assert response.status_code == 200
    html = BeautifulSoup(response.content, "html.parser")
    event_details = html.find_all('div', {"class": "announcement__detail"})
    assert event_details
    assert any(t.find('span', text="1 июля 2019 13:07 — 3 июля 2019 15:07") for t in event_details)
    announcement_details.ends_at = None
    announcement_details.save()
    response = client.get(announcement.get_absolute_url())
    assert response.status_code == 200
    html = BeautifulSoup(response.content, "html.parser")
    event_details = html.find_all('div', {"class": "announcement__detail"})
    assert event_details
    assert any(t.find('span', text="1 июля 2019 13:07 — 3 июля 2019") for t in event_details)