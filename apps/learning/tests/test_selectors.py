import pytest

from courses.models import CourseTeacher
from courses.tests.factories import CourseFactory, CourseTeacherFactory
from learning.selectors import get_teacher_not_spectator_courses
from users.tests.factories import TeacherFactory


@pytest.mark.django_db
def test_get_teacher_not_spectator_courses():
    teacher_one, teacher_two, teacher_three = TeacherFactory.create_batch(3)
    course_one, course_two, course_three = CourseFactory.create_batch(3)
    CourseTeacherFactory(course=course_one, teacher=teacher_one,
                         roles=CourseTeacher.roles.lecturer & CourseTeacher.roles.seminar)
    CourseTeacherFactory(course=course_two, teacher=teacher_one,
                         roles=CourseTeacher.roles.spectator)
    CourseTeacherFactory(course=course_three, teacher=teacher_one,
                         roles=CourseTeacher.roles.organizer)

    CourseTeacherFactory(course=course_one, teacher=teacher_two,
                         roles=CourseTeacher.roles.organizer)
    CourseTeacherFactory(course=course_two, teacher=teacher_two,
                         roles=CourseTeacher.roles.lecturer)

    CourseTeacherFactory(course=course_one, teacher=teacher_three,
                         roles=CourseTeacher.roles.spectator)
    CourseTeacherFactory(course=course_two, teacher=teacher_three,
                         roles=CourseTeacher.roles.spectator)
    CourseTeacherFactory(course=course_three, teacher=teacher_three,
                         roles=CourseTeacher.roles.spectator)

    courses = get_teacher_not_spectator_courses(teacher_one)
    assert len(courses) == 2  # check no duplicates
    assert set(courses) == {course_one, course_three}

    courses = get_teacher_not_spectator_courses(teacher_two)
    assert len(courses) == 2  # check no duplicates
    assert set(courses) == {course_one, course_two}

    courses = get_teacher_not_spectator_courses(teacher_three)
    assert not len(courses)
