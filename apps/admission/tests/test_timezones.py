import datetime

import pytest
import pytz
from bs4 import BeautifulSoup

from admission.constants import InterviewSections
from admission.tests.factories import (
    InterviewFactory, InterviewInvitationFactory, InterviewStreamFactory
)
from core.admin import get_admin_url
from core.models import Branch
from core.tests.factories import BranchFactory, LocationFactory
from core.urls import reverse
# FIXME: этот тест нужно переписать на tz aware datetime field, изначально тест и был так написан, но потом был удалён invitation.stream
from learning.settings import Branches


@pytest.mark.django_db
def test_model(settings):
    """
    Make sure we can save model instance without any implicit timezone
    conversion.
    For example:
        invitation = InterviewInvitation(...)
        invitation.expired_at.tzinfo = nsk_timezone
        invitation.save()
        invitation.refresh_from_db()
        # datetime value (in UTC) equivalent to nsk_timezone
    """
    HOUR = 15  # Make sure (HOUR - nsk utc offset) > 0
    expired_at_naive = datetime.datetime(2017, 1, 1, HOUR, 0, 0, 0)
    with pytest.warns(RuntimeWarning) as record:
        invitation = InterviewInvitationFactory(expired_at=expired_at_naive,
                                                interview__section=InterviewSections.ALL_IN_ONE)
    assert "received a naive datetime" in str(record[0].message)
    # tzinfo have to be None until we explicitly set it or sync data with DB
    assert invitation.expired_at.tzinfo is None
    invitation.refresh_from_db()
    # Now it's aware with UTC timezone because `settings.TIME_ZONE`='UTC'
    assert invitation.expired_at.tzinfo == pytz.UTC
    assert invitation.expired_at.hour == HOUR
    assert invitation.expired_at.minute == 0
    # Update with nsk timezone
    branch_nsk = BranchFactory(code=Branches.NSK)
    value = invitation.expired_at.replace(tzinfo=None)
    invitation.expired_at = branch_nsk.get_timezone().localize(value)
    invitation.save()
    nsk_offset = invitation.expired_at.utcoffset()
    invitation.refresh_from_db()  # nsk tz -> UTC
    td = datetime.timedelta(hours=(HOUR - invitation.expired_at.hour))
    assert td == nsk_offset


@pytest.mark.django_db
def test_get_timezone(settings):
    branch_nsk = BranchFactory(code=Branches.NSK)
    date = datetime.datetime(2017, 1, 1, 15, 0, 0, 0, tzinfo=pytz.UTC)
    interview = InterviewFactory(applicant__campaign__branch=branch_nsk,
                                 section=InterviewSections.ALL_IN_ONE,
                                 date=date)
    assert interview.get_timezone() == branch_nsk.get_timezone()
    branch_spb = Branch.objects.get(code=Branches.SPB, site_id=settings.SITE_ID)
    interview.applicant.campaign.branch = branch_spb
    interview.applicant.campaign.save()
    interview.refresh_from_db()
    branch_spb = BranchFactory(code=Branches.SPB)
    assert interview.get_timezone() == branch_spb.get_timezone()


@pytest.mark.skip("Нужно обязательно переписать этот тест на другое поле, которое точно не изменится :<")
@pytest.mark.django_db
def test_admin_view(settings, admin_client):
    # Datetime widget depends on locale, change it
    settings.LANGUAGE_CODE = 'ru'
    invitation = InterviewInvitationFactory()
    location_in_spb = LocationFactory(city_id='spb')
    location_in_nsk = LocationFactory(city_id='nsk')
    invitation.stream.venue = location_in_spb
    invitation.stream.save()
    stream_for_spb = invitation.stream
    form_data = {
        "applicant": invitation.applicant_id,
        "stream": invitation.stream_id,
        "expired_at_0": "29.06.2017",
        "expired_at_1": "00:00:00",
        "date": "31.05.2017",
        "_continue": "save_and_continue"
    }
    admin_url = get_admin_url(invitation)
    response = admin_client.post(admin_url, form_data, follow=True)
    assert response.status_code == 200
    prev_datetime = invitation.expired_at.replace(tzinfo=pytz.UTC)
    invitation.refresh_from_db()
    assert invitation.expired_at != prev_datetime
    # In SPB we have msk timezone (UTC +3)
    # In DB we store datetime values in UTC
    assert invitation.expired_at.day == 28
    assert invitation.expired_at.hour == 21
    assert invitation.expired_at.minute == 0
    # Admin widget shows localized time
    response = admin_client.get(admin_url)
    widget_html = response.context['adminform'].form['expired_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'expired_at_1'})
    assert time_input.get('value') == '00:00:00'
    date_input = widget.find('input', {"name": 'expired_at_0'})
    assert date_input.get('value') == '29.06.2017'
    # Update stream value with another city
    stream_for_nsk = InterviewStreamFactory(venue=location_in_nsk)
    form_data['stream'] = stream_for_nsk.pk
    response = admin_client.post(admin_url, form_data)
    assert response.status_code == 302
    invitation.refresh_from_db()
    response = admin_client.get(admin_url)
    widget_html = response.context['adminform'].form['expired_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'expired_at_1'})
    assert time_input.get('value') == '00:00:00'
    assert invitation.expired_at.hour == 17  # UTC +7 in nsk
    assert invitation.expired_at.minute == 0
    # Update stream and expired time
    form_data["stream"] = stream_for_spb.pk
    form_data["expired_at_1"] = "06:00:00"
    response = admin_client.post(admin_url, form_data)
    assert response.status_code == 302
    invitation.refresh_from_db()
    response = admin_client.get(admin_url)
    widget_html = response.context['adminform'].form['expired_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'expired_at_1'})
    assert time_input.get('value') == '06:00:00'
    assert invitation.expired_at.hour == 3
    assert invitation.expired_at.minute == 0
    # Update stream and expired_at, but choose values when UTC shouldn't change
    form_data["stream"] = stream_for_nsk.pk
    form_data["expired_at_1"] = "10:00:00"
    response = admin_client.post(admin_url, form_data)
    assert response.status_code == 302
    invitation.refresh_from_db()
    response = admin_client.get(admin_url)
    widget_html = response.context['adminform'].form['expired_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'expired_at_1'})
    assert time_input.get('value') == '10:00:00'
    assert invitation.expired_at.hour == 3
    assert invitation.expired_at.minute == 0
    assert invitation.stream_id == stream_for_nsk.pk
    # Update other field, just to make sure all is OK
    form_data["date"] = "11.06.2017"
    response = admin_client.post(admin_url, form_data)
    assert response.status_code == 302
    invitation.refresh_from_db()
    response = admin_client.get(admin_url)
    widget_html = response.context['adminform'].form['expired_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'expired_at_1'})
    assert time_input.get('value') == '10:00:00'
    assert invitation.expired_at.hour == 3
    # Empty timezone aware field (`stream` for `InterviewInvitation`)
    add_url = reverse('admin:admission_interviewinvitation_add')
    form_data['stream'] = ''
    response = admin_client.post(add_url, form_data, follow=True)
    assert response.status_code == 200
    widget_html = response.context['adminform'].form['expired_at'].as_widget()
    widget = BeautifulSoup(widget_html, "html.parser")
    time_input = widget.find('input', {"name": 'expired_at_1'})
    assert time_input.get('value') == '10:00:00'


@pytest.mark.django_db
def test_interview_list(settings, client, curator):
    client.login(curator)
    settings.LANGUAGE_CODE = 'ru'
    # Add interview for msk timezone
    date_at = datetime.datetime(2017, 1, 1, 15, 0, 0, 0, tzinfo=pytz.UTC)
    interview = InterviewFactory(date=date_at,
                                 section=InterviewSections.ALL_IN_ONE,
                                 applicant__campaign__branch__code=Branches.SPB)
    assert interview.applicant.campaign.branch.code == Branches.SPB
    # We set naive datetime which should been interpreted as UTC
    assert interview.date.hour == 15
    msk_interview_date_in_utc = interview.date
    msk_tz = interview.get_timezone()
    localized = msk_interview_date_in_utc.astimezone(msk_tz)
    time_str = "{:02d}:{:02d}".format(localized.hour, localized.minute)
    assert time_str == '18:00'  # expected UTC+3
    url = reverse("admission:interviews") + "?campaign="
    response = client.get(url)
    assert response.status_code == 200
    html = BeautifulSoup(response.content, "html.parser")

    assert html.find('div', {"class": "time"}, text=time_str) is not None
    # Add interview for nsk timezone
    interview = InterviewFactory(date=datetime.datetime(2017, 1, 1, 12, 0, 0, 0, tzinfo=pytz.UTC),
                                 section=InterviewSections.ALL_IN_ONE)
    branch_nsk = Branch.objects.get(code=Branches.NSK, site_id=settings.SITE_ID)
    interview.applicant.campaign.branch_id = branch_nsk
    interview.applicant.campaign.save()
    interview.refresh_from_db()
    interview_date_in_utc = interview.date
    tz = interview.get_timezone()
    localized = interview_date_in_utc.astimezone(tz)
    time_str = "{:02d}:{:02d}".format(localized.hour, localized.minute)
    assert time_str == "19:00"  # expected UTC + 7
    url = reverse("admission:interviews") + "?campaign="
    response = client.get(url)
    assert response.status_code == 200
    html = BeautifulSoup(response.content, "html.parser")
    assert html.find('div', {"class": "time"}, text=time_str) is not None


@pytest.mark.django_db
def test_interview_detail(settings, client, curator):
    settings.LANGUAGE_CODE = 'ru'
    client.login(curator)
    # Add interview for msk timezone
    dt_at = datetime.datetime(2017, 1, 1, 15, 0, 0, 0, tzinfo=pytz.UTC)
    interview = InterviewFactory(date=dt_at,
                                 section=InterviewSections.ALL_IN_ONE,
                                 applicant__campaign__branch__code=Branches.NSK)
    date_in_utc = interview.date
    branch_nsk = BranchFactory(code=Branches.NSK)
    localized = date_in_utc.astimezone(branch_nsk.get_timezone())
    time_str = "{:02d}:{:02d}".format(localized.hour, localized.minute)
    assert time_str == "22:00"
    response = client.get(interview.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    assert any(time_str in s.string for s in
               html.find_all('div', {"class": "date"}))
    # Make sure timezone doesn't cached on view lvl
    branch_spb = Branch.objects.get(code=Branches.SPB, site_id=settings.SITE_ID)
    interview.applicant.campaign.branch = branch_spb
    interview.applicant.campaign.save()
    localized = date_in_utc.astimezone(branch_spb.get_timezone())
    time_str = "{:02d}:{:02d}".format(localized.hour, localized.minute)
    assert time_str == "18:00"
    response = client.get(interview.get_absolute_url())
    html = BeautifulSoup(response.content, "html.parser")
    assert any(time_str in s.string for s in
               html.find_all('div', {"class": "date"}))
