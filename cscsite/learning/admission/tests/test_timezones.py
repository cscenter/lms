import datetime
import pytest
import pytz
from django.forms import model_to_dict

from core.admin import CityAwareModelForm, get_admin_url
from learning.admission.factories import ApplicantFactory, InterviewFactory, \
    InterviewStreamFactory, InterviewInvitationFactory
from learning.admission.models import InterviewInvitation
from learning.factories import VenueFactory


class InterviewInvitationCityAwareModelForm(CityAwareModelForm):
    class Meta:
        model = InterviewInvitation
        fields = "__all__"


@pytest.mark.django_db
def test_model(settings):
    """
    Make sure we can save model instance without any implicit timezone conversion.
    """
    applicant = ApplicantFactory()
    interview = InterviewFactory(applicant=applicant)
    venue = VenueFactory(city_id='spb')
    stream = InterviewStreamFactory(venue=venue)
    assert stream.venue.city_id == 'spb'
    date = stream.date
    HOUR = 15  # Make sure (HOUR - nsk utc offset) > 0
    expired_at_naive = datetime.datetime(date.year, date.month, date.day,
                                         HOUR, 0, 0, 0)
    invitation = InterviewInvitation(applicant=applicant,
                                     interview=interview,
                                     stream=stream,
                                     date=date,
                                     expired_at=expired_at_naive)
    # tzinfo have to be None until we explicitly set it or sync data with DB
    assert invitation.expired_at.tzinfo is None
    invitation.save()
    assert invitation.expired_at.tzinfo is None
    invitation.refresh_from_db()
    # Now it's aware with UTC timezone because `settings.TIME_ZONE`='UTC'
    assert invitation.expired_at.tzinfo == pytz.UTC
    assert invitation.expired_at.hour == HOUR
    assert invitation.expired_at.minute == 0
    # Update with nsk timezone
    nsk_timezone = settings.TIME_ZONES['nsk']
    value = invitation.expired_at.replace(tzinfo=None)
    invitation.expired_at = nsk_timezone.localize(value)
    invitation.save()
    nsk_offset = invitation.expired_at.utcoffset()
    invitation.refresh_from_db()  # nsk tz -> UTC
    td = datetime.timedelta(hours=(HOUR - invitation.expired_at.hour))
    assert td == nsk_offset


@pytest.mark.django_db
def test_admin(settings, admin_client):
    # Datetime widget depends on locale, change it
    settings.LANGUAGE_CODE = 'ru'
    # expired_at_naive = datetime.datetime(date.year, date.month, date.day,
    #                                      HOUR, 0, 0, 0)
    invitation = InterviewInvitationFactory()
    venue = VenueFactory(city_id='spb')
    invitation.stream.venue = venue
    invitation.stream.save()
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
    prev_datetime = invitation.expired_at.replace(tzinfo='UTC')
    invitation.refresh_from_db()
    assert invitation.expired_at != prev_datetime
    # In SPB we have msk timezone (UTC +3)
    # In DB we store datetime values in UTC
    assert invitation.expired_at.day == 28
    assert invitation.expired_at.hour == 21
    assert invitation.expired_at.minute == 0
    # TODO: Какие тесты нужно написать далее
    """
    0. Залезть в response.context, найти там форму и убедиться, что в виджет попадают верные данные. Либо как-то decompress заценить
    1. Поменять насильно stream.venue на nsk, снова отправить форму и убедиться, что UTC подстроилось
    2. Теперь поменять stream и убедиться, что UTC подстраивается под stream.venue
    3. Поменять и stream и expired_at
    4. Поменять stream  и expired_at так, чтобы при конвертации в naive не было видно разницы (т.е. mks -> nsk но и expired_at +4 часа)
    5. Поменять любое другое поле и убедиться, что ничего не похерилось.
    """
