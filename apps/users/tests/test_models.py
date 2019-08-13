import pytest
from django.core.exceptions import ValidationError

from core.tests.utils import ANOTHER_DOMAIN_ID, TEST_DOMAIN_ID
from learning.tests.factories import EnrollmentFactory
from courses.tests.factories import SemesterFactory, CourseFactory
from learning.settings import StudentStatuses, GradeTypes
from users.constants import Roles
from users.models import User
from users.tests.factories import StudentFactory, CuratorFactory, UserFactory, \
    UserGroupFactory


@pytest.mark.django_db
def test_enrolled_on_the_course():
    student = StudentFactory.create()
    co = CourseFactory()
    assert student.get_enrollment(co.pk) is None
    enrollment = EnrollmentFactory(student=student, course=co)
    assert student.get_enrollment(co.pk) is None  # query was cached
    delattr(student, f"_student_enrollment_{co.pk}")
    assert student.get_enrollment(co.pk) is not None
    curator = CuratorFactory()
    assert curator.get_enrollment(co.pk) is None


@pytest.mark.django_db
def test_user_city_code(client, settings):
    student = StudentFactory.create(city_id='kzn')
    response = client.get('/')
    assert response.wsgi_request.user.city_code is None
    client.login(student)
    response = client.get('/')
    assert response.wsgi_request.user.city_code == 'kzn'


@pytest.mark.django_db
def test_user_add_group(settings):
    settings.SITE_ID = TEST_DOMAIN_ID
    user = User(username="foo", email="foo@localhost.ru")
    user.save()
    user.add_group(Roles.STUDENT)
    assert user.groups.count() == 1
    user_group = user.groups.first()
    assert user_group.site_id == TEST_DOMAIN_ID
    settings.SITE_ID = ANOTHER_DOMAIN_ID
    user = User(username="bar", email="bar@localhost.ru")
    user.save()
    user.add_group(Roles.STUDENT)
    assert user.groups.count() == 1
    user_group = user.groups.first()
    assert user_group.site_id == ANOTHER_DOMAIN_ID


@pytest.mark.django_db
def test_user_add_group_already_exists():
    user = User(username="foo", email="foo@localhost.ru")
    user.save()
    user.add_group(Roles.STUDENT)
    assert user.groups.count() == 1
    user.add_group(Roles.STUDENT)
    assert user.groups.count() == 1


@pytest.mark.django_db
def test_user_remove_group():
    """Test subsequent calls with the same role"""
    user = User(username="foo", email="foo@localhost.ru")
    user.save()
    user.remove_group(Roles.STUDENT)
    user.remove_group(Roles.STUDENT)


@pytest.mark.django_db
def test_roles(settings):
    user = UserFactory(groups=[Roles.STUDENT,
                               Roles.TEACHER])
    assert set(user.roles) == {Roles.STUDENT, Roles.TEACHER}
    user.status = StudentStatuses.EXPELLED
    user.groups.add(UserGroupFactory(user=user, role=Roles.VOLUNTEER))
    # Invalidate cache
    del user.site_groups
    del user.roles
    assert user.roles == {Roles.TEACHER,
                          Roles.STUDENT,
                          Roles.VOLUNTEER}
    user.groups.all().delete()
    user.add_group(role=Roles.STUDENT)
    user.status = ''
    user.save()
    settings.SITE_ID = settings.CLUB_SITE_ID
    del user.site_groups
    del user.roles
    assert not set(user.site_groups)


@pytest.mark.django_db
def test_passed_courses():
    """Make sure courses not counted twice in passed courses stat"""
    student = StudentFactory()
    co1, co2, co3 = CourseFactory.create_batch(3)
    # enrollments 1 and 4 for the same course but from different terms
    e1, e2, e3 = (EnrollmentFactory(course=co,
                                    student=student,
                                    grade=GradeTypes.GOOD)
                  for co in (co1, co2, co3))
    next_term = SemesterFactory.create_next(co1.semester)
    co4 = CourseFactory(meta_course=co1.meta_course, is_open=False,
                        semester=next_term)
    e4 = EnrollmentFactory(course=co4, student=student, grade=GradeTypes.GOOD)
    stats = student.stats(next_term)
    assert stats['passed']['total'] == 3
    e4.grade = GradeTypes.UNSATISFACTORY
    e4.save()
    stats = student.stats(next_term)
    assert stats['passed']['total'] == 3
    e2.grade = GradeTypes.UNSATISFACTORY
    e2.save()
    stats = student.stats(next_term)
    assert stats['passed']['total'] == 2


def test_github_id_validation():
    user = UserFactory.build()
    with pytest.raises(ValidationError):
        user.github_id = "mikhail--m"
        user.clean_fields()
    with pytest.raises(ValidationError):
        user.github_id = "mikhailm-"
        user.clean_fields()
    with pytest.raises(ValidationError):
        user.github_id = "mikhailm--"
        user.clean_fields()
    with pytest.raises(ValidationError):
        user.github_id = "-mikhailm"
        user.clean_fields()
    user.github_id = "mikhailm"
    user.clean_fields()
    user.github_id = "mikhail-m"
    user.clean_fields()
    user.github_id = "m-i-k-h-a-i-l-m"
    user.clean_fields()


def test_get_abbreviated_short_name():
    non_breaking_space = chr(160)
    user = UserFactory.build()
    user.username = "mikhail"
    user.first_name = "Misha"
    user.last_name = "Ivanov"
    assert user.get_abbreviated_short_name() == f"Ivanov{non_breaking_space}M."
    assert user.get_abbreviated_short_name(last_name_first=False) == f"M.{non_breaking_space}Ivanov"
    user.first_name = ""
    assert user.get_abbreviated_short_name() == "Ivanov"
    user.last_name = ""
    assert user.get_abbreviated_short_name() == "mikhail"
