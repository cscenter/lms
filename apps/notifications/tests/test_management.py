from io import StringIO as OutputIO
from unittest.mock import MagicMock

import pytest
import pytz

from django.core import mail, management

from core.tests.factories import BranchFactory
from courses.constants import SemesterTypes
from courses.tests.factories import SemesterFactory
from courses.utils import TermPair
from learning.models import AssignmentNotification
from learning.tests.factories import (
    AssignmentNotificationFactory, CourseFactory, CourseNewsNotificationFactory,
    EnrollmentFactory
)
from notifications.management.commands.notify import resolve_course_participant_branch
from users.tests.factories import CuratorFactory, UserFactory, TeacherFactory


@pytest.mark.django_db
def test_command_notify(settings, mocker):
    mocker.patch('core.locks.get_shared_connection', MagicMock())
    settings.DEFAULT_URL_SCHEME = 'https'
    out = OutputIO()
    mail.outbox = []
    management.call_command("notify", stdout=out)
    assert len(mail.outbox) == 0
    assert len(out.getvalue()) == 0

    out = OutputIO()
    mail.outbox = []
    an = AssignmentNotificationFactory(is_about_passed=True)
    management.call_command("notify", stdout=out)
    if settings.ENABLE_NON_AUTH_NOTIFICATIONS:
        assert len(mail.outbox) == 1
        assert AssignmentNotification.objects.get(pk=an.pk).is_notified
        assert "sending notification for" in out.getvalue()
    else:
        assert not mail.outbox
        assert not AssignmentNotification.objects.get(pk=an.pk).is_notified
        assert "sending notification for" not in out.getvalue()

    out = OutputIO()
    mail.outbox = []
    management.call_command("notify", stdout=out)
    assert len(mail.outbox) == 0
    assert len(out.getvalue()) == 0

    out = OutputIO()
    mail.outbox = []
    conn = CourseNewsNotificationFactory.create()
    management.call_command("notify", stdout=out)
    if settings.ENABLE_NON_AUTH_NOTIFICATIONS:
        assert len(mail.outbox) == 1
        conn.refresh_from_db()
        assert conn.is_notified
        assert "sending notification for" in out.getvalue()
    else:
        assert not mail.outbox
        conn.refresh_from_db()
        assert not conn.is_notified
        assert "sending notification for" not in out.getvalue()

    out = OutputIO()
    mail.outbox = []
    user = UserFactory(is_notification_allowed=False)
    an = AssignmentNotificationFactory(is_about_passed=True, user=user)
    management.call_command("notify", stdout=out)
    assert not mail.outbox
    assert not AssignmentNotification.objects.get(pk=an.pk).is_notified
    assert "sending notification for" not in out.getvalue()

@pytest.mark.django_db
def test_command_notification_cleanup(client, settings):
    current_term = SemesterFactory.create_current()
    semester = TermPair(year=current_term.academic_year - 1,
                        type=SemesterTypes.AUTUMN)
    notification1, notification2 = AssignmentNotificationFactory.create_batch(
        2, is_notified=True, is_unread=False)
    notification1.created = semester.starts_at(pytz.UTC)
    notification1.save()
    out = OutputIO()
    management.call_command("notification_cleanup", stdout=out)
    assert "1 AssignmentNotifications" in out.getvalue()
    assert AssignmentNotification.objects.filter(pk=notification2.pk).exists()


@pytest.mark.django_db
def test_resolve_course_participant_branch():
    curator = CuratorFactory()
    main_branch = BranchFactory()
    teacher = TeacherFactory(branch=BranchFactory())
    other_teacher = TeacherFactory(branch=BranchFactory())
    course = CourseFactory(main_branch=main_branch, teachers=[teacher])
    enrollment = EnrollmentFactory(course=course)
    student = enrollment.student
    assert resolve_course_participant_branch(course, teacher) == course.main_branch
    assert resolve_course_participant_branch(course, other_teacher) == course.main_branch
    assert resolve_course_participant_branch(course, curator) == course.main_branch
    assert resolve_course_participant_branch(course, student) == enrollment.student_profile.branch
