"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".
Replace this with more appropriate tests for your application.
"""
from core.tests.utils import CSCTestCase
from users.tests.factories import UserFactory

try:
    # Django >= 1.7
    from django.test import override_settings
except ImportError:
    # Django <= 1.6
    from django.test.utils import override_settings

import pytz

from django.conf import settings
from django.utils import timezone
from django.utils.timezone import localtime, utc

from notifications.models import Notification
from notifications.signals import notify


class NotificationTest(CSCTestCase):

    @override_settings(USE_TZ=True)
    @override_settings(TIME_ZONE='Asia/Shanghai')
    def test_use_timezone(self):

        from_user = UserFactory.create(username="from", password="pwd", email="example@example.com")
        to_user = UserFactory.create(username="to", password="pwd", email="example2@example.com")
        from notifications import NotificationTypes
        notify.send(from_user, type=NotificationTypes.LOG,
                    recipient=to_user, verb='commented',
                    action_object=from_user)
        notification = Notification.objects.get(recipient=to_user)
        delta = timezone.now().replace(tzinfo=utc) - localtime(notification.timestamp, pytz.timezone(settings.TIME_ZONE))
        self.assertTrue(delta.seconds < 60)
        # The delta between the two events will still be less than a second despite the different timezones
        # The call to now and the immediate call afterwards will be within a short period of time, not 8 hours as the
        # test above was originally.
