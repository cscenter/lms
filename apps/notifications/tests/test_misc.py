import pytest
import pytz

from django.utils import timezone
from django.utils.timezone import localtime, utc

from notifications.models import Notification
from notifications.signals import notify
from users.tests.factories import UserFactory


@pytest.mark.django_db
def test_use_timezone(settings):
    settings.USE_TZ = True
    settings.TIME_ZONE = 'Asia/Shanghai'
    from_user = UserFactory(username="from", password="pwd", email="example@example.com")
    to_user = UserFactory(username="to", password="pwd", email="example2@example.com")
    from notifications import NotificationTypes
    notify.send(from_user, type=NotificationTypes.LOG,
                recipient=to_user, verb='commented',
                action_object=from_user)
    notification = Notification.objects.get(recipient=to_user)
    delta = timezone.now().replace(tzinfo=utc) - localtime(notification.timestamp, pytz.timezone(settings.TIME_ZONE))
    assert delta.seconds < 60
    # The delta between the two events will still be less than a second despite the different timezones
    # The call to now and the immediate call afterwards will be within a short period of time, not 8 hours as the
    # test above was originally.
