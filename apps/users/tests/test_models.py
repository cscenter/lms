import pytest

from django.core.exceptions import ValidationError

from core.tests.factories import BranchFactory
from core.tests.settings import ANOTHER_DOMAIN_ID, TEST_DOMAIN_ID
from core.utils import instance_memoize
from courses.tests.factories import CourseFactory, SemesterFactory
from learning.settings import GradeTypes
from learning.tests.factories import EnrollmentFactory
from users.constants import Roles
from users.tests.factories import (
    CuratorFactory, StudentFactory, StudentProfileFactory, UserFactory, UserGroupFactory
)


@pytest.mark.django_db
def test_enrolled_on_the_course(settings):
    student = StudentFactory.create()
    co = CourseFactory()
    assert student.get_enrollment(co.pk) is None
    student_profile = student.get_student_profile(settings.SITE_ID)
    enrollment = EnrollmentFactory(student=student, course=co,
                                   student_profile=student_profile)
    assert student.get_enrollment(co.pk) is None  # query was cached
    instance_memoize.delete_cache(student)
    assert student.get_enrollment(co.pk) is not None
    curator = CuratorFactory()
    assert curator.get_enrollment(co.pk) is None


@pytest.mark.django_db
def test_user_add_group(settings):
    settings.SITE_ID = TEST_DOMAIN_ID
    user = UserFactory()
    user.save()
    user.add_group(Roles.INTERVIEWER)
    assert user.groups.count() == 1
    user_group = user.groups.first()
    assert user_group.site_id == TEST_DOMAIN_ID
    settings.SITE_ID = ANOTHER_DOMAIN_ID
    user = UserFactory()
    user.save()
    user.add_group(Roles.INTERVIEWER)
    assert user.groups.count() == 1
    user_group = user.groups.first()
    assert user_group.site_id == ANOTHER_DOMAIN_ID


@pytest.mark.django_db
def test_user_add_group_already_exists():
    user = UserFactory()
    user.save()
    user.add_group(Roles.CURATOR)
    assert user.groups.count() == 1
    user.add_group(Roles.CURATOR)
    assert user.groups.count() == 1


@pytest.mark.django_db
def test_user_remove_group():
    """Test subsequent calls with the same role"""
    user = UserFactory()
    user.save()
    user.remove_group(Roles.STUDENT)
    user.remove_group(Roles.STUDENT)


@pytest.mark.django_db
def test_roles(settings, mocker):
    mocker.patch('code_reviews.gerrit.tasks.update_password_in_gerrit')
    user = StudentFactory(groups=[Roles.TEACHER])
    assert set(user.roles) == {Roles.STUDENT, Roles.TEACHER}
    UserGroupFactory(user=user, role=Roles.INTERVIEWER)
    # Invalidate cache
    user.refresh_from_db()
    del user.roles
    del user.site_groups
    instance_memoize.delete_cache(user)
    assert user.roles == {Roles.TEACHER,
                          Roles.STUDENT,
                          Roles.INTERVIEWER}
    user.groups.all().delete()
    user.add_group(role=Roles.STUDENT)
    user.save()
    settings.SITE_ID = settings.CLUB_SITE_ID
    user.refresh_from_db()
    instance_memoize.delete_cache(user)
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
    co4 = CourseFactory(meta_course=co1.meta_course, semester=next_term)
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


@pytest.mark.django_db
def test_github_login_validation():
    user = UserFactory.build()
    with pytest.raises(ValidationError):
        user.github_login = "mikhail--m"
        user.clean_fields()
    with pytest.raises(ValidationError):
        user.github_login = "mikhailm-"
        user.clean_fields()
    with pytest.raises(ValidationError):
        user.github_login = "mikhailm--"
        user.clean_fields()
    with pytest.raises(ValidationError):
        user.github_login = "-mikhailm"
        user.clean_fields()
    user.github_login = "mikhailm"
    user.clean_fields()
    user.github_login = "mikhail-m"
    user.clean_fields()
    user.github_login = "m-i-k-h-a-i-l-m"
    user.clean_fields()


@pytest.mark.django_db
def test_telegram_username_validation(settings):
    user = UserFactory.build()
    with pytest.raises(ValidationError):
        # too short
        user.telegram_username = "user"
        user.clean_fields()
    with pytest.raises(ValidationError):
        # leading symbol should be a-zA-Z
        user.telegram_username = "1user"
        user.clean_fields()
    with pytest.raises(ValidationError):
        # double underscores prohibited
        user.telegram_username = "us__er"
        user.clean_fields()
    with pytest.raises(ValidationError):
        # should end with a-zA-Z0-9
        user.telegram_username = "u5er_"
        user.clean_fields()
    with pytest.raises(ValidationError):
        # hyphens are prohibited
        user.telegram_username = "u5-er"
        user.clean_fields()
    # blank = True
    user.telegram_username = ""
    user.clean_fields()
    user.telegram_username = "u5_er"
    user.clean_fields()
    user.telegram_username = "u1234"
    user.clean_fields()
    user.telegram_username = "u_s_e_r"
    user.clean_fields()


@pytest.mark.django_db
def test_student_profile_year_of_admission():
    branch = BranchFactory(established=2011)
    with pytest.raises(ValidationError):
        StudentProfileFactory(branch=branch, year_of_admission=2010)
    student_profile = StudentProfileFactory(branch=branch, year_of_admission=2011)
    assert student_profile.pk


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
