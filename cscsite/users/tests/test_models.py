import pytest
from django.core.exceptions import ValidationError

from learning.factories import CourseFactory, EnrollmentFactory, \
    SemesterFactory
from learning.settings import AcademicRoles, GRADES, \
    StudentStatuses
from users.factories import StudentFactory, CuratorFactory, UserFactory, \
    StudentCenterFactory


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
def test_cached_groups(settings):
    user = UserFactory.create()
    user.groups.add(AcademicRoles.STUDENT_CENTER,
                    AcademicRoles.TEACHER_CENTER)
    assert set(user._cached_groups) == {AcademicRoles.STUDENT_CENTER,
                                        AcademicRoles.TEACHER_CENTER}
    user.status = StudentStatuses.expelled
    user.groups.add(AcademicRoles.VOLUNTEER)
    # Invalidate property cache
    del user._cached_groups
    # Nothing change!
    assert user._cached_groups == {AcademicRoles.TEACHER_CENTER,
                                   AcademicRoles.STUDENT_CENTER,
                                   AcademicRoles.VOLUNTEER}
    # Add student club group for center students on club site
    user.groups.clear()
    del user._cached_groups
    user.groups.add(AcademicRoles.STUDENT_CENTER)
    user.status = ''
    user.save()
    settings.SITE_ID = settings.CLUB_SITE_ID
    assert set(user._cached_groups) == {AcademicRoles.STUDENT_CENTER,
                                        AcademicRoles.STUDENT_CLUB}


@pytest.mark.django_db
def test_permissions(client):
    current_semester = SemesterFactory.create_current()
    # Unauthenticated user
    response = client.get("/")
    request_user = response.wsgi_request.user
    assert not request_user.is_authenticated
    assert not request_user.is_student_center
    assert not request_user.is_student_club
    assert not request_user.is_student
    assert not request_user.is_volunteer
    assert not request_user.is_active_student
    assert not request_user.is_master_student
    assert not request_user.is_teacher_center
    assert not request_user.is_teacher_club
    assert not request_user.is_teacher
    assert not request_user.is_graduate
    assert not request_user.is_curator
    assert not request_user.is_curator_of_projects
    assert not request_user.is_interviewer
    assert not request_user.is_project_reviewer
    # Active student
    student = StudentCenterFactory(status='')
    client.login(student)
    response = client.get("/")
    request_user = response.wsgi_request.user
    assert request_user.is_authenticated
    assert request_user.is_student_center
    assert not request_user.is_student_club
    assert request_user.is_student
    assert not request_user.is_volunteer
    assert request_user.is_active_student
    assert not request_user.is_master_student
    assert not request_user.is_teacher_center
    assert not request_user.is_teacher_club
    assert not request_user.is_teacher
    assert not request_user.is_graduate
    assert not request_user.is_curator
    assert not request_user.is_curator_of_projects
    assert not request_user.is_interviewer
    assert not request_user.is_project_reviewer
    # Expelled student
    student.status = StudentStatuses.expelled
    student.save()
    response = client.get("/")
    request_user = response.wsgi_request.user
    assert request_user.is_authenticated
    assert request_user.is_student_center
    assert not request_user.is_student_club
    assert request_user.is_student
    assert not request_user.is_volunteer
    assert not request_user.is_active_student
    assert not request_user.is_master_student
    assert not request_user.is_teacher_center
    assert not request_user.is_teacher_club
    assert not request_user.is_teacher
    assert not request_user.is_graduate
    assert not request_user.is_curator
    assert not request_user.is_curator_of_projects
    assert not request_user.is_interviewer
    assert not request_user.is_project_reviewer


@pytest.mark.django_db
def test_passed_courses():
    """Make sure courses not counted twice in passed courses stat"""
    student = StudentFactory()
    co1, co2, co3 = CourseFactory.create_batch(3)
    # enrollments 1 and 4 for the same course but from different terms
    e1, e2, e3 = (EnrollmentFactory(course=co,
                                    student=student,
                                    grade=GRADES.good)
                  for co in (co1, co2, co3))
    next_term = SemesterFactory.create_next(co1.semester)
    co4 = CourseFactory(meta_course=co1.meta_course, is_open=False,
                        semester=next_term)
    e4 = EnrollmentFactory(course=co4, student=student, grade=GRADES.good)
    stats = student.stats(next_term)
    assert stats['passed']['total'] == 3
    e4.grade = GRADES.unsatisfactory
    e4.save()
    stats = student.stats(next_term)
    assert stats['passed']['total'] == 3
    e2.grade = GRADES.unsatisfactory
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
    user = UserFactory.build()
    user.username = "mikhail"
    user.first_name = "Misha"
    user.last_name = "Ivanov"
    assert user.get_abbreviated_short_name() == "Ivanov M."
    assert user.get_abbreviated_short_name(last_name_first=False) == "M. Ivanov"
    user.first_name = ""
    assert user.get_abbreviated_short_name() == "Ivanov"
    user.last_name = ""
    assert user.get_abbreviated_short_name() == "mikhail"
