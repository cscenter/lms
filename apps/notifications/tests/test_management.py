from io import StringIO as OutputIO
from unittest.mock import MagicMock

import pytest

from django.core import mail, management

from core.tests.factories import BranchFactory
from learning.models import AssignmentNotification
from learning.tests.factories import (
    AssignmentNotificationFactory, CourseFactory, CourseNewsNotificationFactory,
    EnrollmentFactory
)
from notifications.management.commands.notify import resolve_course_participant_branch
from users.tests.factories import CuratorFactory, StudentFactory, TeacherFactory


@pytest.mark.django_db
def test_notifications(client, settings, mocker):
    mocker.patch('core.locks.get_shared_connection', MagicMock())
    settings.DEFAULT_URL_SCHEME = 'https'
    out = OutputIO()
    mail.outbox = []
    management.call_command("notify", stdout=out)
    assert len(mail.outbox) == 0
    assert len(out.getvalue()) == 0

    out = OutputIO()
    mail.outbox = []
    student = StudentFactory()
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
    student = StudentFactory()
    conn = CourseNewsNotificationFactory.create(user=student)
    course = conn.course_offering_news.course
    management.call_command("notify", stdout=out)
    assert len(mail.outbox) == 1
    conn.refresh_from_db()
    assert conn.is_notified
    assert course.get_absolute_url() in mail.outbox[0].body
    assert "sending notification for" in out.getvalue()


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