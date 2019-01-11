from django.test import SimpleTestCase

from users.constants import AcademicRoles
from users.factories import UserFactory

# Workaround to use Django's assertRedirects()
_STS = SimpleTestCase()


def assert_redirects(*args, **kwargs):
    # Deprecated. Use pytest fixture instead
    _STS.assertRedirects(*args, **kwargs)


def assert_login_redirect(client, settings, url):
    assert_redirects(client.get(url),
                     "{}?next={}".format(settings.LOGIN_URL, url))


def check_url_security(client, settings, groups_allowed, url):
    """
    Checks if only users in groups listed in `groups_allowed` can
    access the page which url is stored in `url`.
    Also checks that curator can access any page.
    """
    assert_redirects(client.get(url),
                     "{}?next={}".format(settings.LOGIN_URL, url))
    all_test_groups = [
        [],
        [AcademicRoles.TEACHER_CENTER],
        [AcademicRoles.STUDENT_CENTER],
        [AcademicRoles.GRADUATE_CENTER]
    ]
    for groups in all_test_groups:
        client.login(UserFactory.create(groups=groups, city_id='spb'))
        if any(g in groups_allowed for g in groups):
            assert client.get(url).status_code == 200
        else:
            # assert login redirect
            assert_redirects(client.get(url),
                             "{}?next={}".format(settings.LOGIN_URL, url))
        client.logout()
    client.login(UserFactory.create(is_superuser=True, is_staff=True,
                                    city_id='spb'))
    assert client.get(url).status_code == 200


def flatten_calendar_month_events(calendar_month):
    return [calendar_event.event for week in calendar_month.weeks()
            for day in week.days
            for calendar_event in day.events]
