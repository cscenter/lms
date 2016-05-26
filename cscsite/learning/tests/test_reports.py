# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

import pytest

from django.utils.encoding import smart_bytes

from learning.factories import SemesterFactory, CourseOfferingFactory, \
    EnrollmentFactory, StudentProjectFactory
from learning.reports import ProgressReportForDiplomas, ProgressReportFull
from learning.settings import GRADES, STUDENT_STATUS, GRADING_TYPES
from learning.utils import get_term_by_index
from staff.views import StudentsInfoForDiplomasMixin
from users.factories import SHADCourseRecordFactory, OnlineCourseRecordFactory
from users.models import CSCUser



@pytest.mark.django_db
def test_report_common(client):
    # TODO: нам нужно убедиться, что заголовок соответствует данным. Может достаточно только на уровне контекста проверить
    # TODO: тестировать 1. онлайн-курсы 2. шад 3. курсы центра (это и клуба) 4. проекта
    # TODO: test "Max count values"
    pass


@pytest.mark.django_db
def test_report_full(rf,
                     student_center_factory,
                     teacher_center_factory):
    """
    Looks the same as diplomas report, but including online courses, some
    additional info (like total successful passed courses)
    """
    def get_progress_report():
        students_data = CSCUser.objects.students_info()
        return ProgressReportFull(students_data,
                                  honest_grade_system=True,
                                  request=rf)
    teacher = teacher_center_factory.create()
    students = student_center_factory.create_batch(3)
    s = SemesterFactory.create_current()
    co1, co2 = CourseOfferingFactory.create_batch(2, semester=s,
                                                  teachers=[teacher])
    student1, student2, student3 = students
    student1.status = STUDENT_STATUS.will_graduate
    student1.save()
    EnrollmentFactory.create(student=student1, course_offering=co1,
                             grade=GRADES.good)
    progress_report = get_progress_report()
    STATIC_HEADERS_CNT = len(progress_report.static_headers)
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 2
    # Without grade not included
    EnrollmentFactory.create(student=student2, course_offering=co2,
                             grade=GRADES.not_graded)
    progress_report = get_progress_report()
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 2
    # Online course included. +1 header
    OnlineCourseRecordFactory.create(student=student1)
    progress_report = get_progress_report()
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 3


@pytest.mark.django_db
def test_report_for_term_common(client):
    #TODO: затестить passed_success_in_target_semester, он одинаковый
    # TODO: passed_success_total тоже. И enrollments_in_target_semester
    # TODO: проверить, что курсы ШАД не входящие в выбранный семестр не включаются в файл
    # TODO: убедиться, что курсы, не входящие в целевой, в data не попадают (только учитываются в стате)
    # Входят курсы центра и клуба
    # TODO: не попадают выпускники
    # TODO: честные оценки honest_grade_system

    pass


@pytest.mark.django_db
def test_report_for_current_term(client):
    # TODO: Затестить, что в data попадают курсы без оценок
    # TODO: ШАД и онлайн не входят
    pass


@pytest.mark.django_db
def test_report_for_any_passed_term(client):
    # TODO: ШАД и онлайн входят
    pass


@pytest.mark.django_db
def test_report_diplomas(student_center_factory,
                         teacher_center_factory):
    get_students_info = StudentsInfoForDiplomasMixin.get_students_info
    teacher = teacher_center_factory.create()
    students = student_center_factory.create_batch(3)
    s = SemesterFactory.create_current()
    prev_term_year, prev_term_type = get_term_by_index(s.index - 1)
    prev_s = SemesterFactory.create(year=prev_term_year, type=prev_term_type)
    co_prev1 = CourseOfferingFactory.create(semester=prev_s, teachers=[teacher])
    co1 = CourseOfferingFactory.create(semester=s, teachers=[teacher])
    student1, student2, student3 = students
    student1.status = STUDENT_STATUS.will_graduate
    student1.save()
    e_s1_co1 = EnrollmentFactory.create(student=student1, course_offering=co1,
                                        grade=GRADES.good)
    EnrollmentFactory.create(student=student2, course_offering=co1,
                             grade=GRADES.good)
    students_data = StudentsInfoForDiplomasMixin.get_students_info()
    # Will graduate only student1 now
    assert len(students_data) == 1
    progress_report = ProgressReportForDiplomas(students_data)
    assert len(progress_report.data) == 1
    # This value will not change during all tests
    STATIC_HEADERS_CNT = len(progress_report.static_headers)
    # No we have 1 passed enrollment for student1, so +2 headers except static
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 2
    # student2 will graduate too. He enrolled to the same course as student1
    student2.status = STUDENT_STATUS.will_graduate
    student2.save()
    progress_report = ProgressReportForDiplomas(get_students_info())
    assert len(progress_report.data) == 2
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 2
    # Enroll student2 to new course without any grade
    co2 = CourseOfferingFactory.create(semester=s, teachers=[teacher])
    e_s2_co2 = EnrollmentFactory.create(student=student2, course_offering=co2)
    progress_report = ProgressReportForDiplomas(get_students_info())
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 2
    # Now change grade to unsatisfied and check again
    e_s2_co2.grade = GRADES.unsatisfactory
    e_s2_co2.save()
    progress_report = ProgressReportForDiplomas(get_students_info())
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 2
    # Set success grade value
    e_s2_co2.grade = GRADES.good
    e_s2_co2.save()
    progress_report = ProgressReportForDiplomas(get_students_info())
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 4
    # Grade should be printed with `default` grading type style
    e_s1_co1.grade = getattr(GRADES, "pass")
    e_s1_co1.save()
    co1.grading_type = GRADING_TYPES.binary
    co1.save()
    progress_report = ProgressReportForDiplomas(get_students_info())
    assert progress_report.data[0].pk == student1.pk
    grade_values = [d.get("grade", "") for d in progress_report.data[0].courses.values()]
    assert smart_bytes("satisfactory") not in grade_values
    # Add enrollment for previous term. It should be appeared if grade OK
    EnrollmentFactory.create(student=student1, course_offering=co_prev1,
                             grade=GRADES.good)
    progress_report = ProgressReportForDiplomas(get_students_info())
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 6
    # Add shad course
    SHADCourseRecordFactory.create(student=student1, grade=GRADES.good)
    # this one shouldn't be in file due to grade value
    # FIXME: no it's included (code below)??? FIX or good behavior?
    # SHADCourseRecordFactory.create(student=student1, grade=GRADES.not_graded)
    progress_report = ProgressReportForDiplomas(get_students_info())
    # +3 headers for 1 shad course
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 9
    # Online course not included
    OnlineCourseRecordFactory.create(student=student1)
    progress_report = ProgressReportForDiplomas(get_students_info())
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 9
    StudentProjectFactory.create(students=[student1, student2])
    progress_report = ProgressReportForDiplomas(get_students_info())
    # +4 headers for project
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 13
    # FIXME: Should test data, don't trust headers!
