from io import StringIO as OutputIO

import pytest
from django.core import mail, management

from learning.models import AssignmentNotification
from learning.tests.factories import AssignmentNotificationFactory, \
    CourseNewsNotificationFactory
from notifications.management.commands.notify import get_base_domain
from users.constants import AcademicRoles
from users.tests.factories import UserFactory, StudentCenterFactory


@pytest.mark.django_db
def test_notifications(client, settings):
    # FIXME: Make this as a default setting for test env?
    settings.DEFAULT_URL_SCHEME = 'https'
    out = OutputIO()
    mail.outbox = []
    management.call_command("notify", stdout=out)
    assert len(mail.outbox) == 0
    assert len(out.getvalue()) == 0

    out = OutputIO()
    mail.outbox = []
    student = StudentCenterFactory()
    an = AssignmentNotificationFactory(is_about_passed=True,
                                       user=student)
    management.call_command("notify", stdout=out)
    assert len(mail.outbox) == 1
    assert AssignmentNotification.objects.get(pk=an.pk).is_notified
    assert an.student_assignment.get_teacher_url() in mail.outbox[0].body
    assert "sending notification for" in out.getvalue()

    out = OutputIO()
    mail.outbox = []
    management.call_command("notify", stdout=out)
    assert len(mail.outbox) == 0
    assert len(out.getvalue()) == 0

    out = OutputIO()
    mail.outbox = []
    student = StudentCenterFactory()
    conn = CourseNewsNotificationFactory.create(user=student)
    course = conn.course_offering_news.course
    management.call_command("notify", stdout=out)
    assert len(mail.outbox) == 1
    conn.refresh_from_db()
    assert conn.is_notified
    assert course.get_absolute_url() in mail.outbox[0].body
    assert "sending notification for" in out.getvalue()


@pytest.mark.django_db
def test_notify_get_base_url():
    """Site domain in notifications depends on recipient user groups"""
    user = UserFactory(groups=[AcademicRoles.STUDENT_CENTER])
    notification = AssignmentNotificationFactory(user=user)
    assert get_base_domain(notification) == "my.compscicenter.ru"
    user = UserFactory(groups=[AcademicRoles.STUDENT_CENTER,
                               AcademicRoles.STUDENT_CLUB])
    notification = AssignmentNotificationFactory(user=user)
    assert get_base_domain(notification) == "my.compscicenter.ru"
    notification.user = UserFactory(groups=[AcademicRoles.STUDENT_CLUB])
    assert get_base_domain(notification) == "compsciclub.ru"
    notification.user = UserFactory(groups=[AcademicRoles.STUDENT_CENTER,
                                            AcademicRoles.TEACHER_CLUB])
    assert get_base_domain(notification) == "my.compscicenter.ru"
    notification.user = UserFactory(groups=[AcademicRoles.TEACHER_CLUB])
    assert get_base_domain(notification) == "compsciclub.ru"
    notification.user = UserFactory(groups=[AcademicRoles.TEACHER_CLUB,
                                            AcademicRoles.GRADUATE_CENTER])
    assert get_base_domain(notification) == "my.compscicenter.ru"
