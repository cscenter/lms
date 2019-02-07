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

from django.conf import settings
from django.utils.timezone import utc, localtime
from django.utils import timezone
import pytz

from notifications.signals import notify
from notifications.models import Notification


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

# FIXME: fuck it, rewrite with pytest
# class NotificationManagersTest(CSCTestCase):
#
#     def setUp(self):
#         self.message_count = 10
#         self.from_user = UserFactory.create(username="from2", password="pwd", email="example@example.com")
#         self.to_user = UserFactory.create(username="to2", password="pwd", email="example@example.com")
#         self.to_group = Group.objects.create(name="to2_g")
#         self.to_group.user_set.add(self.to_user)
#         for i in range(self.message_count):
#             notify.send(self.from_user, recipient=self.to_user, verb='commented', action_object=self.from_user)
#         # Send notification to group
#         notify.send(self.from_user, recipient=self.to_group, verb='commented', action_object=self.from_user)
#         self.message_count += 1
#
#     def test_unread_manager(self):
#         self.assertEqual(Notification.objects.unread().count(), self.message_count)
#         n = Notification.objects.filter(recipient=self.to_user).first()
#         n.mark_as_read()
#         self.assertEqual(Notification.objects.unread().count(), self.message_count-1)
#         for n in Notification.objects.unread():
#             self.assertTrue(n.unread)
#
#     def test_read_manager(self):
#         self.assertEqual(Notification.objects.unread().count(), self.message_count)
#         n = Notification.objects.filter(recipient=self.to_user).first()
#         n.mark_as_read()
#         self.assertEqual(Notification.objects.read().count(), 1)
#         for n in Notification.objects.read():
#             self.assertFalse(n.unread)
#
#     def test_mark_all_as_read_manager(self):
#         self.assertEqual(Notification.objects.unread().count(), self.message_count)
#         Notification.objects.filter(recipient=self.to_user).mark_all_as_read()
#         self.assertEqual(Notification.objects.unread().count(), 0)
#
#     @override_settings(NOTIFICATIONS_SOFT_DELETE=True)
#     def test_mark_all_as_read_manager_with_soft_delete(self):
#         # even soft-deleted notifications should be marked as read
#         # refer: https://github.com/django-notifications/django-notifications/issues/126
#         to_delete = Notification.objects.filter(recipient=self.to_user).order_by('id')[0]
#         to_delete.deleted = True
#         to_delete.save()
#         self.assertTrue(Notification.objects.filter(recipient=self.to_user).order_by('id')[0].unread)
#         Notification.objects.filter(recipient=self.to_user).mark_all_as_read()
#         self.assertFalse(Notification.objects.filter(recipient=self.to_user).order_by('id')[0].unread)
#
#     def test_mark_all_as_unread_manager(self):
#         self.assertEqual(Notification.objects.unread().count(), self.message_count)
#         Notification.objects.filter(recipient=self.to_user).mark_all_as_read()
#         self.assertEqual(Notification.objects.unread().count(), 0)
#         Notification.objects.filter(recipient=self.to_user).mark_all_as_unread()
#         self.assertEqual(Notification.objects.unread().count(), self.message_count)
#
#     @override_settings(NOTIFICATIONS_SOFT_DELETE=True)
#     def test_mark_all_deleted_manager(self):
#         n = Notification.objects.filter(recipient=self.to_user).first()
#         n.mark_as_read()
#         self.assertEqual(Notification.objects.read().count(), 1)
#         self.assertEqual(Notification.objects.unread().count(), self.message_count-1)
#         self.assertEqual(Notification.objects.active().count(), self.message_count)
#         self.assertEqual(Notification.objects.deleted().count(), 0)
#
#         Notification.objects.mark_all_as_deleted()
#         self.assertEqual(Notification.objects.read().count(), 0)
#         self.assertEqual(Notification.objects.unread().count(), 0)
#         self.assertEqual(Notification.objects.active().count(), 0)
#         self.assertEqual(Notification.objects.deleted().count(), self.message_count)
#
#         Notification.objects.mark_all_as_active()
#         self.assertEqual(Notification.objects.read().count(), 1)
#         self.assertEqual(Notification.objects.unread().count(), self.message_count-1)
#         self.assertEqual(Notification.objects.active().count(), self.message_count)
#         self.assertEqual(Notification.objects.deleted().count(), 0)
