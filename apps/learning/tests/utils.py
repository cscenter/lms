from users.constants import Roles
from users.tests.factories import UserFactory


def check_url_security(client, assert_login_redirect, groups_allowed, url):
    """
    Checks if only users in groups listed in `groups_allowed` can
    access the page which url is stored in `url`.
    Also checks that curator can access any page.
    """
    assert_login_redirect(url, method='get')
    all_test_groups = [
        [],
        [Roles.TEACHER],
        [Roles.STUDENT],
        [Roles.GRADUATE]
    ]
    for groups in all_test_groups:
        client.login(UserFactory.create(groups=groups, city_id='spb'))
        if any(g in groups_allowed for g in groups):
            assert client.get(url).status_code == 200
        else:
            assert_login_redirect(url, method='get')
        client.logout()
    client.login(UserFactory.create(is_superuser=True, is_staff=True,
                                    city_id='spb'))
    assert client.get(url).status_code == 200


def flatten_calendar_month_events(calendar_month):
    return [calendar_event.event for week in calendar_month.weeks()
            for day in week.days
            for calendar_event in day.events]
