# -*- coding: utf-8 -*-

import pytest
from django.utils.encoding import smart_bytes

from core.models import Branch
from core.tests.factories import BranchFactory
from courses.utils import get_term_by_index
from learning.reports import ProgressReportForDiplomas, ProgressReportFull, \
    ProgressReportForSemester
from learning.settings import GradingSystems, StudentStatuses, GradeTypes, \
    Branches
from learning.tests.factories import SemesterFactory, CourseFactory, \
    EnrollmentFactory
from projects.filters import SupervisorGradeFilter
from projects.tests.factories import ProjectFactory, SupervisorFactory
from users.constants import Roles
from users.tests.factories import SHADCourseRecordFactory, \
    OnlineCourseRecordFactory, TeacherFactory, StudentFactory


def check_value_for_header(report, header, row_index, expected_value):
    """
    Make sure that `header` in report headers.
    Value related to `header` for data[row_index] should be
    equal to `expected_value`
    """
    assert header in report.headers
    header_index = report.headers.index(header)
    export_data = report.export_row(report.data[row_index])
    assert export_data[header_index] == expected_value


@pytest.mark.django_db
def test_report_common():
    def get_progress_report():
        return ProgressReportFull(honest_grade_system=True)
    teacher = TeacherFactory.create()
    s = SemesterFactory.create_current()
    co1, co2, co3 = CourseFactory.create_batch(3, semester=s,
                                               teachers=[teacher])
    student1, student2, student3 = StudentFactory.create_batch(3)
    EnrollmentFactory(student=student1, course=co1, grade=GradeTypes.GOOD)
    EnrollmentFactory(student=student2, course=co1, grade=GradeTypes.GOOD)
    EnrollmentFactory(student=student2, course=co2, grade=GradeTypes.NOT_GRADED)
    shad1 = SHADCourseRecordFactory(student=student1, grade=GradeTypes.GOOD)
    shad2 = SHADCourseRecordFactory(student=student2, grade=GradeTypes.GOOD)
    p = ProjectFactory.create(students=[student1], semester=s)
    supervisor = SupervisorFactory()
    p.supervisors.add(supervisor.pk)
    ps = p.projectstudent_set.all()[0]  # 1 student attached
    ps.final_grade = GradeTypes.EXCELLENT
    ps.save()
    progress_report = get_progress_report()
    assert len(progress_report.courses_headers) == 2
    assert progress_report.online_courses_max == 0
    assert progress_report.shads_max == 1
    assert progress_report.projects_max == 1
    student1_row_index = 0
    student2_row_index = 1
    student3_row_index = 2
    assert progress_report.data[student1_row_index].pk == student1.pk
    assert progress_report.data[student2_row_index].pk == student2.pk
    assert progress_report.data[student3_row_index].pk == student3.pk
    # Check project headers and values
    check_value_for_header(progress_report, 'Проект 1, название',
                           student1_row_index, p.name)
    check_value_for_header(progress_report, 'Проект 1, оценка',
                           student1_row_index, ps.get_final_grade_display())
    supervisors = [s.get_abbreviated_name() for s in p.supervisors.all()]
    check_value_for_header(progress_report, 'Проект 1, руководитель(и)',
                           student1_row_index, supervisors)
    check_value_for_header(progress_report, 'Проект 1, семестр',
                           student1_row_index, p.semester)
    check_value_for_header(progress_report, 'Проект 1, название',
                           student2_row_index, '')
    assert 'Проект 2, название' not in progress_report.headers
    # Check shad courses headers and values
    assert 'ШАД, курс 2, название' not in progress_report.headers
    check_value_for_header(progress_report, 'ШАД, курс 1, название',
                           student1_row_index, shad1.name)
    check_value_for_header(progress_report, 'ШАД, курс 1, преподаватели',
                           student1_row_index, shad1.teachers)
    check_value_for_header(progress_report, 'ШАД, курс 1, оценка',
                           student1_row_index, shad1.grade_display.lower())
    check_value_for_header(progress_report, 'ШАД, курс 1, название',
                           student2_row_index, shad2.name)
    check_value_for_header(progress_report, 'ШАД, курс 1, преподаватели',
                           student2_row_index, shad2.teachers)
    check_value_for_header(progress_report, 'ШАД, курс 1, оценка',
                           student2_row_index, shad2.grade_display.lower())
    check_value_for_header(progress_report, 'Проект 1, название',
                           student3_row_index, '')
    # No added online-courses, but it should be displayed in progress
    assert 'Онлайн-курс 1, название' not in progress_report.headers
    # Add project for 2 students and check grades
    p2 = ProjectFactory.create(students=[student1, student2],
                               semester=s)
    for ps in p2.projectstudent_set.all():
        if ps.student == student1:
            ps.final_grade = GradeTypes.EXCELLENT
            ps.save()
        elif ps.student == student2:
            ps.final_grade = GradeTypes.GOOD
            ps.save()
    progress_report = get_progress_report()
    assert progress_report.projects_max == 2
    assert 'Проект 2, название' in progress_report.headers
    # Order by semester first, then by project name
    assert p.name < p2.name
    check_value_for_header(progress_report, 'Проект 2, название',
                           student1_row_index, p2.name)
    check_value_for_header(progress_report, 'Проект 2, оценка',
                           student1_row_index, GradeTypes.EXCELLENT.title())
    # It's first project for student2
    check_value_for_header(progress_report, 'Проект 1, название',
                           student2_row_index, p2.name)
    check_value_for_header(progress_report, 'Проект 1, оценка',
                           student2_row_index, GradeTypes.GOOD.title())


@pytest.mark.django_db
def test_report_full():
    """
    Looks the same as diplomas report, but including online courses, some
    additional info (like total successful passed courses)
    """
    def get_progress_report():
        return ProgressReportFull(honest_grade_system=True)

    STATIC_HEADERS_CNT = len(get_progress_report().generate_headers())
    teacher = TeacherFactory.create()
    students = StudentFactory.create_batch(3)
    s = SemesterFactory.create_current()
    co1, co2 = CourseFactory.create_batch(2, semester=s,
                                          teachers=[teacher])
    student1, student2, student3 = students
    student1.status = StudentStatuses.WILL_GRADUATE
    student1.save()
    EnrollmentFactory.create(student=student1, course=co1, grade=GradeTypes.GOOD)
    progress_report = get_progress_report()
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 2
    # Without grade included too
    EnrollmentFactory.create(student=student2, course=co2,
                             grade=GradeTypes.NOT_GRADED)
    progress_report = get_progress_report()
    assert len(progress_report.courses_headers) == 2
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 4
    # Online course included. +1 header
    OnlineCourseRecordFactory.create(student=student1)
    progress_report = get_progress_report()
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 5
    EnrollmentFactory.create(student=student1, course=co2,
                             grade=GradeTypes.GOOD)
    EnrollmentFactory.create(student=student2, course=co1,
                             grade=GradeTypes.GOOD)
    EnrollmentFactory.create(student=student3, course=co1,
                             grade=GradeTypes.UNSATISFACTORY)
    progress_report = get_progress_report()
    total_passed_header = 'Успешно сдано курсов (Центр/Клуб/ШАД/Онлайн) всего'
    assert total_passed_header in progress_report.headers
    # Check successfully passed courses value
    assert progress_report.data[0].pk == student1.pk
    # 2 co and 1 online course
    check_value_for_header(progress_report, total_passed_header, 0, 2 + 1)
    assert progress_report.data[1].pk == student2.pk
    SHADCourseRecordFactory.create(student=student2, grade=GradeTypes.NOT_GRADED)
    # skip `not_graded` course and shad course for student2 in stat column
    check_value_for_header(progress_report, total_passed_header, 1, 1)
    assert progress_report.data[2].pk == student3.pk
    check_value_for_header(progress_report, total_passed_header, 2, 0)
    # Add well graded shad course to student1
    SHADCourseRecordFactory.create(student=student1, grade=GradeTypes.GOOD)
    # 2 co, 1 online course and 1 shad course
    progress_report = get_progress_report()
    check_value_for_header(progress_report, total_passed_header, 0, 2 + 1 + 1)
    # TODO: check excluded in report
    # TODO: check grading_type


@pytest.mark.django_db
def test_report_for_target_term():

    def get_progress_report(term):
        return ProgressReportForSemester(term,
                                         honest_grade_system=True)
    teacher = TeacherFactory.create()
    s = SemesterFactory.create_current()
    STATIC_HEADERS_CNT = len(get_progress_report(s).generate_headers())
    prev_term_year, prev_term_type = get_term_by_index(s.index - 1)
    prev_s = SemesterFactory.create(year=prev_term_year, type=prev_term_type)
    co_active = CourseFactory.create(semester=s, teachers=[teacher])
    co1, co2, co3 = CourseFactory.create_batch(3, semester=prev_s,
                                               teachers=[teacher])
    student1, student2, student3 = StudentFactory.create_batch(3)
    e_active = EnrollmentFactory.create(student=student1,
                                        course=co_active,
                                        grade=GradeTypes.EXCELLENT)
    e_active2 = EnrollmentFactory.create(student=student2,
                                         course=co_active,
                                         grade=GradeTypes.NOT_GRADED)
    e_old1 = EnrollmentFactory.create(student=student1, course=co1,
                                      grade=GradeTypes.GOOD)
    e_old2 = EnrollmentFactory.create(student=student2, course=co1,
                                      grade=GradeTypes.NOT_GRADED)
    progress_report = get_progress_report(prev_s)
    assert len(progress_report.data) == 3
    # Graduated students not included in report
    student3.groups.all().delete()
    student3.add_group(Roles.GRADUATE)
    progress_report = get_progress_report(prev_s)
    assert len(progress_report.data) == 2
    CENTER_CLUB_COURSES_HEADERS_CNT = 1
    # `co_active` headers not in report for passed term
    assert len(progress_report.headers) == (STATIC_HEADERS_CNT +
                                            CENTER_CLUB_COURSES_HEADERS_CNT)
    assert co_active.meta_course.name not in progress_report.headers
    # Check `not_graded` values included for passed target term
    student1_data_index = 0
    student2_data_index = 1
    assert progress_report.data[student2_data_index].pk == student2.pk
    course_header_grade = '{}, оценка'.format(co1.meta_course.name)
    assert course_header_grade in progress_report.headers
    check_value_for_header(progress_report, course_header_grade,
                           student2_data_index, e_old2.grade_display.lower())
    # And included for current target term. Compare expected value with actual
    progress_report = get_progress_report(s)
    assert len(progress_report.headers) == (STATIC_HEADERS_CNT +
                                            CENTER_CLUB_COURSES_HEADERS_CNT)
    course_header_grade = '{}, оценка'.format(co_active.meta_course.name)
    assert progress_report.data[student1_data_index].pk == student1.pk
    check_value_for_header(progress_report, course_header_grade,
                           student1_data_index, e_active.grade_display.lower())
    assert progress_report.data[student2_data_index].pk == student2.pk
    check_value_for_header(progress_report, course_header_grade,
                           student2_data_index, e_active2.grade_display.lower())
    # Shad and online courses from prev semester not included in report
    shad = SHADCourseRecordFactory.create(student=student1, grade=GradeTypes.GOOD,
                                          semester=prev_s)
    shad_header = 'ШАД, курс 1, название'
    progress_report = get_progress_report(s)
    assert shad_header not in progress_report.headers
    progress_report = get_progress_report(prev_s)
    assert shad_header in progress_report.headers
    check_value_for_header(progress_report, shad_header,
                           student1_data_index, shad.name)
    # Check honest grade system
    e = EnrollmentFactory.create(student=student1, course=co2,
                                 grade=GradeTypes.CREDIT)
    progress_report = get_progress_report(prev_s)
    assert progress_report.data[student1_data_index].pk == student1.pk
    course_header_grade = '{}, оценка'.format(co2.meta_course.name)
    check_value_for_header(progress_report, course_header_grade,
                           student1_data_index, e.grade_honest.lower())
    # Test `success_total_lt_target_semester` value
    success_total_lt_ts_header = (
        'Успешно сдано (Центр/Клуб/ШАД/Онлайн) всего до семестра "%s"' % prev_s)
    success_total_eq_ts_header = (
        'Успешно сдано (Центр/Клуб/ШАД) за семестр "%s"' % prev_s)
    # +2 successful enrollments and +1 shad course for prev_s
    check_value_for_header(progress_report, success_total_lt_ts_header,
                           student1_data_index, 0)
    check_value_for_header(progress_report, success_total_eq_ts_header,
                           student1_data_index, 3)
    # And 1 successful enrollment in current semester
    progress_report = get_progress_report(s)
    success_total_lt_ts_header = (
        'Успешно сдано (Центр/Клуб/ШАД/Онлайн) всего до семестра "%s"' % s)
    success_total_eq_ts_header = (
        'Успешно сдано (Центр/Клуб/ШАД) за семестр "%s"' % s)
    check_value_for_header(progress_report, success_total_lt_ts_header,
                           student1_data_index, 3)
    check_value_for_header(progress_report, success_total_eq_ts_header,
                           student1_data_index, 1)
    # Hide shad courses from semester less than target semester
    assert progress_report.shads_max == 0
    # Add not_graded shad course for current semester. We show it for
    # target semester, but it's not counted in stats
    SHADCourseRecordFactory.create(student=student1,
                                   grade=GradeTypes.NOT_GRADED,
                                   semester=s)
    progress_report = get_progress_report(s)
    assert progress_report.shads_max == 1
    check_value_for_header(progress_report, success_total_lt_ts_header,
                           student1_data_index, 3)
    check_value_for_header(progress_report, success_total_eq_ts_header,
                           student1_data_index, 1)
    # TODO: Test enrollments_in_target_semester


@pytest.mark.django_db
def test_report_diplomas_csv(settings):
    teacher = TeacherFactory.create()
    student1, student2, student3 = StudentFactory.create_batch(
        3, branch__code=Branches.SPB)
    s = SemesterFactory.create_current()
    STATIC_HEADERS_CNT = len(ProgressReportForDiplomas().generate_headers())
    prev_term_year, prev_term_type = get_term_by_index(s.index - 1)
    prev_s = SemesterFactory.create(year=prev_term_year, type=prev_term_type)
    co_prev1 = CourseFactory.create(semester=prev_s, teachers=[teacher])
    co1 = CourseFactory.create(semester=s, teachers=[teacher])
    student1.status = StudentStatuses.WILL_GRADUATE
    student1.save()
    e_s1_co1 = EnrollmentFactory.create(student=student1, course=co1,
                                        grade=GradeTypes.GOOD)
    EnrollmentFactory.create(student=student2, course=co1, grade=GradeTypes.GOOD)
    # Will graduate only student1 now
    progress_report = ProgressReportForDiplomas()
    assert len(progress_report.data) == 1
    # No we have 1 passed enrollment for student1, so +2 headers except static
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 2
    # student2 will graduate too. He enrolled to the same course as student1
    student2.status = StudentStatuses.WILL_GRADUATE
    student2.save()
    progress_report = ProgressReportForDiplomas()
    assert len(progress_report.data) == 2
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 2
    # Enroll student2 to new course without any grade
    co2 = CourseFactory.create(semester=s, teachers=[teacher])
    e_s2_co2 = EnrollmentFactory.create(student=student2, course=co2)
    progress_report = ProgressReportForDiplomas()
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 2
    # Now change grade to unsatisfied and check again
    e_s2_co2.grade = GradeTypes.UNSATISFACTORY
    e_s2_co2.save()
    progress_report = ProgressReportForDiplomas()
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 2
    # Set success grade value
    e_s2_co2.grade = GradeTypes.GOOD
    e_s2_co2.save()
    progress_report = ProgressReportForDiplomas()
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 4
    # Grade should be printed with `default` grading type style
    e_s1_co1.grade = GradeTypes.CREDIT
    e_s1_co1.save()
    co1.grading_type = GradingSystems.BINARY
    co1.save()
    progress_report = ProgressReportForDiplomas()
    assert progress_report.data[0].pk == student1.pk
    grade_values = [d.get("grade", "") for d
                    in progress_report.data[0].courses.values()]
    assert smart_bytes("satisfactory") not in grade_values
    # Add enrollment for previous term. It should be appeared if grade OK
    EnrollmentFactory.create(student=student1, course=co_prev1,
                             grade=GradeTypes.GOOD)
    progress_report = ProgressReportForDiplomas()
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 6
    # Add shad course
    SHADCourseRecordFactory(student=student1, grade=GradeTypes.GOOD)
    # This one shouldn't be in report due to grade value
    SHADCourseRecordFactory(student=student1, grade=GradeTypes.NOT_GRADED)
    progress_report = ProgressReportForDiplomas()
    # +3 headers for 1 shad course
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 9
    # Online course not included
    OnlineCourseRecordFactory.create(student=student1)
    progress_report = ProgressReportForDiplomas()
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 9
    ProjectFactory.create(students=[student1, student2])
    progress_report = ProgressReportForDiplomas()
    # +4 headers for project
    assert len(progress_report.headers) == STATIC_HEADERS_CNT + 13

    student1.branch = Branch.objects.get_by_natural_key(Branches.NSK,
                                                        settings.SITE_ID)
    student1.save()
    progress_report = ProgressReportForDiplomas()
    assert len(progress_report.data) == 2


@pytest.mark.django_db
def test_report_diplomas_by_branch():
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    s1, s2, s3 = StudentFactory.create_batch(3, branch=branch_spb)
    s1.status = StudentStatuses.WILL_GRADUATE
    s1.save()
    s2.status = StudentStatuses.WILL_GRADUATE
    s2.save()
    progress_report = ProgressReportForDiplomas()
    assert len(progress_report.data) == 2
    progress_report = ProgressReportForDiplomas(qs_filters={
        "branch_id": branch_spb.pk
    })
    assert len(progress_report.data) == 2
    progress_report = ProgressReportForDiplomas(qs_filters={
        "branch_id": branch_nsk.pk
    })
    assert len(progress_report.data) == 0
    s3.status = StudentStatuses.WILL_GRADUATE
    s3.branch = branch_nsk
    s3.save()
    progress_report = ProgressReportForDiplomas(qs_filters={
        "branch_id": branch_spb.pk
    })
    assert len(progress_report.data) == 2
    progress_report = ProgressReportForDiplomas(qs_filters={
        "branch_id": branch_nsk.pk
    })
    assert len(progress_report.data) == 1
    assert progress_report.data[0].pk == s3.pk
