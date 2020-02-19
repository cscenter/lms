from io import StringIO as OutputIO

import pytest
from django.core import mail, management

from core.tests.factories import BranchFactory, SiteFactory
from learning.models import AssignmentNotification
from learning.tests.factories import AssignmentNotificationFactory, \
    CourseNewsNotificationFactory
from notifications.management.commands.notify import _get_base_domain
from users.constants import Roles
from users.tests.factories import UserFactory, StudentFactory, TeacherFactory


@pytest.mark.django_db
def test_notifications(client, settings):
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
@pytest.mark.parametrize("notification_factory",  [AssignmentNotificationFactory, CourseNewsNotificationFactory])
def test_notify_get_base_url(notification_factory, settings):
    settings.LMS_SUBDOMAIN = 'my'
    branch = BranchFactory(site=SiteFactory(domain='test.domain'))
    user = UserFactory(branch=branch)
    notification = notification_factory(user=user)
    assert _get_base_domain(notification) == f"{settings.LMS_SUBDOMAIN}.test.domain"
    # Test subdomain resolving (supported on club site)
    settings.LMS_SUBDOMAIN = None
    new_branch = BranchFactory()
    notification.user.branch = new_branch
    settings.DEFAULT_BRANCH_CODE = new_branch.code
    settings.CLUB_SITE_ID = new_branch.site_id
    assert _get_base_domain(notification) == new_branch.site.domain
    branch_code = f"xyz{new_branch.code}"
    new_branch.code = branch_code
    assert _get_base_domain(notification) == f"{branch_code}.{new_branch.site.domain}"
