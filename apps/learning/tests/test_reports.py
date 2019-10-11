# -*- coding: utf-8 -*-

import pytest
from django.utils.encoding import smart_bytes
from pandas import DataFrame

from core.models import Branch
from core.tests.factories import BranchFactory
from courses.utils import get_term_by_index
from learning.reports import ProgressReportForDiplomas, ProgressReportFull, \
    ProgressReportForSemester, ProgressReport
from learning.settings import GradingSystems, StudentStatuses, GradeTypes, \
    Branches
from learning.tests.factories import SemesterFactory, CourseFactory, \
    EnrollmentFactory
from projects.constants import ProjectTypes
from projects.filters import SupervisorGradeFilter
from projects.models import Project
from projects.tests.factories import ProjectFactory, SupervisorFactory, \
    ProjectStudentFactory
from users.constants import Roles
from users.tests.factories import SHADCourseRecordFactory, \
    OnlineCourseRecordFactory, TeacherFactory, StudentFactory


def check_value_for_header(report, header, row_index, expected_value):
    assert header in report.columns
    assert report.loc[row_index, header] == expected_value


@pytest.mark.django_db
def test_report_common():
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
    report_factory = ProgressReportFull(grade_getter="grade_honest")
    progress_report = report_factory.generate()
    assert progress_report.index[0] == student1.pk
    assert progress_report.index[1] == student2.pk
    assert progress_report.index[2] == student3.pk
    # Check project headers and associated values
    project_headers = report_factory.generate_projects_headers(1)
    assert project_headers[0] == 'Проект 1, название'
    assert project_headers[1] == 'Проект 1, оценка'
    assert project_headers[2] == 'Проект 1, руководители'
    assert project_headers[3] == 'Проект 1, семестр'
    s1 = report_factory.get_queryset().get(pk=student1.pk)
    s2 = report_factory.get_queryset().get(pk=student2.pk)
    s3 = report_factory.get_queryset().get(pk=student3.pk)
    project_columns = report_factory._export_projects(s1, 1)
    assert project_columns[0] == p.name
    assert project_columns[1] == ps.get_final_grade_display()
    supervisors = ', '.join(s.get_abbreviated_name() for s in
                            p.supervisors.all())
    assert project_columns[2] == supervisors
    assert project_columns[3] == p.semester
    assert 'Проект 2, название' not in project_headers
    # Check shad courses headers/values consistency
    shad_headers = report_factory.generate_shad_courses_headers(1)
    assert shad_headers[0] == 'ШАД, курс 1, название'
    assert shad_headers[1] == 'ШАД, курс 1, преподаватели'
    assert shad_headers[2] == 'ШАД, курс 1, оценка'
    student1_shad = report_factory._export_shad_courses(s1, shads_max=1)
    student2_shad = report_factory._export_shad_courses(s2, shads_max=1)
    student3_shad = report_factory._export_shad_courses(s3, shads_max=1)
    assert student1_shad[0] == shad1.name
    assert student1_shad[1] == shad1.teachers
    assert student1_shad[2] == shad1.grade_display.lower()
    assert student2_shad[0] == shad2.name
    assert student2_shad[1] == shad2.teachers
    assert student2_shad[2] == shad2.grade_display.lower()
    assert student3_shad[0] == ''
    assert student3_shad[1] == ''
    assert student3_shad[2] == ''


@pytest.mark.django_db
def test_report_full():
    """
    Looks the same as diplomas report, but including online courses, some
    additional info (like total successful passed courses)
    """
    report_generator = ProgressReportFull(grade_getter="grade_honest")

    teacher = TeacherFactory.create()
    students = StudentFactory.create_batch(3)
    s = SemesterFactory.create_current()
    co1, co2 = CourseFactory.create_batch(2, semester=s,
                                          teachers=[teacher])
    student1, student2, student3 = students
    student1.status = StudentStatuses.WILL_GRADUATE
    student1.save()
    EnrollmentFactory.create(student=student1, course=co1, grade=GradeTypes.GOOD)
    EnrollmentFactory.create(student=student2, course=co2,
                             grade=GradeTypes.NOT_GRADED)
    OnlineCourseRecordFactory.create(student=student1)
    EnrollmentFactory.create(student=student1, course=co2,
                             grade=GradeTypes.GOOD)
    EnrollmentFactory.create(student=student2, course=co1,
                             grade=GradeTypes.GOOD)
    EnrollmentFactory.create(student=student3, course=co1,
                             grade=GradeTypes.UNSATISFACTORY)
    progress_report = report_generator.generate()
    total_passed_header = 'Успешно сдано курсов (Центр/Клуб/ШАД/Онлайн) всего'
    assert total_passed_header in progress_report.columns
    # Check successfully passed courses value
    assert progress_report.index[0] == student1.pk
    check_value_for_header(progress_report, total_passed_header, student1.pk,
                           expected_value=3)
    assert progress_report.index[1] == student2.pk
    SHADCourseRecordFactory.create(student=student2, grade=GradeTypes.NOT_GRADED)
    # skip `not_graded` course and shad course for student2 in stat column
    check_value_for_header(progress_report, total_passed_header, student2.pk,
                           expected_value=1)
    assert progress_report.index[2] == student3.pk
    check_value_for_header(progress_report, total_passed_header, student3.pk,
                           expected_value=0)
    # Add well graded shad course to student1
    SHADCourseRecordFactory.create(student=student1, grade=GradeTypes.GOOD)
    # 2 co, 1 online course and 1 shad course
    progress_report = report_generator.generate()
    check_value_for_header(progress_report, total_passed_header, student1.pk,
                           expected_value=4)
    # Test projects
    practice_header = 'Пройдено семестров практики(закончили, успех)'
    research_header = 'Пройдено семестров НИР (закончили, успех)'
    ps = ProjectStudentFactory(student=student1,
                               final_grade=GradeTypes.EXCELLENT,
                               project__project_type=ProjectTypes.research)
    ProjectStudentFactory(student=student2,
                          final_grade=GradeTypes.NOT_GRADED,
                          project__project_type=ProjectTypes.research)
    ProjectStudentFactory(student=student2,
                          final_grade=GradeTypes.UNSATISFACTORY,
                          project__project_type=ProjectTypes.practice)
    # Grade is mistakenly good, but project is canceled
    ProjectStudentFactory(student=student2,
                          final_grade=GradeTypes.EXCELLENT,
                          project__status=Project.Statuses.CANCELED)
    progress_report = report_generator.generate()
    check_value_for_header(progress_report, practice_header, student1.pk,
                           expected_value=0)
    check_value_for_header(progress_report, research_header, student1.pk,
                           expected_value=1)
    check_value_for_header(progress_report, practice_header, student2.pk,
                           expected_value=0)
    check_value_for_header(progress_report, research_header, student2.pk,
                           expected_value=0)
    # TODO: check excluded in report
    # TODO: check grading_type


@pytest.mark.django_db
def test_report_for_target_term():

    def get_progress_report(term) -> DataFrame:
        return ProgressReportForSemester(term).generate()
    teacher = TeacherFactory.create()
    s = SemesterFactory.create_current()
    STATIC_HEADERS_CNT = len(get_progress_report(s).columns)
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
    assert len(progress_report) == 3
    # Graduated students not included in report
    student3.groups.all().delete()
    student3.add_group(Roles.GRADUATE)
    progress_report = get_progress_report(prev_s)
    assert len(progress_report) == 2
    CENTER_CLUB_COURSES_HEADERS_CNT = 1
    # `co_active` headers not in report for passed term
    assert len(progress_report.columns) == (STATIC_HEADERS_CNT +
                                            CENTER_CLUB_COURSES_HEADERS_CNT)
    assert co_active.meta_course.name not in progress_report.columns
    # Check `not_graded` values included for passed target term
    student1_data_index = 0
    student2_data_index = 1
    assert progress_report.index[student2_data_index] == student2.pk
    course_header_grade = '{}, оценка'.format(co1.meta_course.name)
    check_value_for_header(progress_report, course_header_grade,
                           student2.pk, e_old2.grade_display.lower())
    # And included for current target term. Compare expected value with actual
    progress_report = get_progress_report(s)
    assert len(progress_report.columns) == (STATIC_HEADERS_CNT +
                                            CENTER_CLUB_COURSES_HEADERS_CNT)
    course_header_grade = '{}, оценка'.format(co_active.meta_course.name)
    assert progress_report.index[student1_data_index] == student1.pk
    check_value_for_header(progress_report, course_header_grade,
                           student1.pk, e_active.grade_display.lower())
    assert progress_report.index[student2_data_index] == student2.pk
    check_value_for_header(progress_report, course_header_grade,
                           student2.pk, e_active2.grade_display.lower())
    # Shad and online courses from prev semester not included in report
    shad = SHADCourseRecordFactory.create(student=student1, grade=GradeTypes.GOOD,
                                          semester=prev_s)
    shad_header = 'ШАД, курс 1, название'
    progress_report = get_progress_report(s)
    assert shad_header not in progress_report.columns
    progress_report = get_progress_report(prev_s)
    assert shad_header in progress_report.columns
    check_value_for_header(progress_report, shad_header,
                           student1.pk, shad.name)
    # Check honest grade system
    e = EnrollmentFactory.create(student=student1, course=co2,
                                 grade=GradeTypes.CREDIT)
    progress_report = get_progress_report(prev_s)
    assert progress_report.index[student1_data_index] == student1.pk
    course_header_grade = '{}, оценка'.format(co2.meta_course.name)
    check_value_for_header(progress_report, course_header_grade,
                           student1.pk, e.grade_honest.lower())
    # Test `success_total_lt_target_semester` value
    success_total_lt_ts_header = (
        'Успешно сдано (Центр/Клуб/ШАД/Онлайн) до семестра "%s"' % prev_s)
    success_total_eq_ts_header = (
        'Успешно сдано (Центр/Клуб/ШАД) за семестр "%s"' % prev_s)
    # +2 successful enrollments and +1 shad course for prev_s
    check_value_for_header(progress_report, success_total_lt_ts_header,
                           student1.pk, 0)
    check_value_for_header(progress_report, success_total_eq_ts_header,
                           student1.pk, 3)
    # And 1 successful enrollment in current semester
    progress_report = get_progress_report(s)
    success_total_lt_ts_header = (
        'Успешно сдано (Центр/Клуб/ШАД/Онлайн) до семестра "%s"' % s)
    success_total_eq_ts_header = (
        'Успешно сдано (Центр/Клуб/ШАД) за семестр "%s"' % s)
    check_value_for_header(progress_report, success_total_lt_ts_header,
                           student1.pk, 3)
    check_value_for_header(progress_report, success_total_eq_ts_header,
                           student1.pk, 1)
    # Hide shad courses from semester less than target semester
    shad_headers = ProgressReport.generate_shad_courses_headers(1)
    assert not any(h in progress_report.columns for h in shad_headers)
    # Add not_graded shad course for current semester. We show it for
    # target semester, but it's not counted in stats
    SHADCourseRecordFactory.create(student=student1,
                                   grade=GradeTypes.NOT_GRADED,
                                   semester=s)
    progress_report = get_progress_report(s)
    assert all(h in progress_report.columns for h in shad_headers)
    check_value_for_header(progress_report, success_total_lt_ts_header,
                           student1.pk, 3)
    check_value_for_header(progress_report, success_total_eq_ts_header,
                           student1.pk, 1)
    # TODO: Test enrollments_in_target_semester


@pytest.mark.django_db
def test_report_diplomas_csv(settings):
    def get_report() -> DataFrame:
        return ProgressReportForDiplomas().generate()

    STATIC_HEADERS_CNT = len(get_report().columns)
    teacher = TeacherFactory.create()
    student1, student2, student3 = StudentFactory.create_batch(
        3, branch__code=Branches.SPB)
    s = SemesterFactory.create_current()
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
    progress_report = get_report()
    assert len(progress_report) == 1
    # No we have 1 passed enrollment for student1, so +2 headers except static
    assert len(progress_report.columns) == STATIC_HEADERS_CNT + 2
    # student2 will graduate too. He enrolled to the same course as student1
    student2.status = StudentStatuses.WILL_GRADUATE
    student2.save()
    progress_report = get_report()
    assert len(progress_report) == 2
    assert len(progress_report.columns) == STATIC_HEADERS_CNT + 2
    # Enroll student2 to new course without any grade
    co2 = CourseFactory.create(semester=s, teachers=[teacher])
    e_s2_co2 = EnrollmentFactory.create(student=student2, course=co2)
    progress_report = get_report()
    assert len(progress_report.columns) == STATIC_HEADERS_CNT + 2
    # Now change grade to unsatisfied and check again
    e_s2_co2.grade = GradeTypes.UNSATISFACTORY
    e_s2_co2.save()
    progress_report = get_report()
    assert len(progress_report.columns) == STATIC_HEADERS_CNT + 2
    # Set success grade value
    e_s2_co2.grade = GradeTypes.GOOD
    e_s2_co2.save()
    progress_report = get_report()
    assert len(progress_report.columns) == STATIC_HEADERS_CNT + 4
    # Grade should be printed with `default` grading type style
    e_s1_co1.grade = GradeTypes.CREDIT
    e_s1_co1.save()
    co1.grading_type = GradingSystems.BINARY
    co1.save()
    progress_report = get_report()
    assert progress_report.index[0] == student1.pk

    for e in student1.enrollment_set.all():
        expected_value = e.grade_display.lower()
        assert expected_value != smart_bytes("satisfactory")
        check_value_for_header(progress_report,
                               f'{e.course.meta_course.name}, оценка',
                               student1.pk, expected_value)
    # Add enrollment for previous term. It should be appeared if grade OK
    EnrollmentFactory.create(student=student1, course=co_prev1,
                             grade=GradeTypes.GOOD)
    progress_report = ProgressReportForDiplomas().generate()
    assert len(progress_report.columns) == STATIC_HEADERS_CNT + 6
    # Add shad course
    SHADCourseRecordFactory(student=student1, grade=GradeTypes.GOOD)
    # This one shouldn't be in report due to grade value
    SHADCourseRecordFactory(student=student1, grade=GradeTypes.NOT_GRADED)
    progress_report = get_report()
    # +3 headers for 1 shad course
    assert len(progress_report.columns) == STATIC_HEADERS_CNT + 9
    # Online course not included
    OnlineCourseRecordFactory.create(student=student1)
    progress_report = get_report()
    assert len(progress_report.columns) == STATIC_HEADERS_CNT + 9
    ProjectFactory.create(students=[student1, student2])
    progress_report = get_report()
    # +4 headers for project
    assert len(progress_report.columns) == STATIC_HEADERS_CNT + 13

    student1.branch = Branch.objects.get_by_natural_key(Branches.NSK,
                                                        settings.SITE_ID)
    student1.save()
    progress_report = get_report()
    assert len(progress_report) == 2


@pytest.mark.django_db
def test_report_diplomas_by_branch():
    branch_spb = BranchFactory(code=Branches.SPB)
    branch_nsk = BranchFactory(code=Branches.NSK)
    s1, s2, s3 = StudentFactory.create_batch(3, branch=branch_spb)
    s1.status = StudentStatuses.WILL_GRADUATE
    s1.save()
    s2.status = StudentStatuses.WILL_GRADUATE
    s2.save()
    progress_report = ProgressReportForDiplomas().generate()
    assert len(progress_report) == 2
    progress_report = ProgressReportForDiplomas()
    qs = progress_report.get_queryset().filter(branch_id=branch_spb.pk)
    progress_report = progress_report.generate(qs)
    assert len(progress_report) == 2
    progress_report = ProgressReportForDiplomas()
    qs = progress_report.get_queryset().filter(branch_id=branch_nsk.pk)
    assert qs.count() == 0
    progress_report = progress_report.generate(queryset=qs)
    assert len(progress_report) == 0
    s3.status = StudentStatuses.WILL_GRADUATE
    s3.branch = branch_nsk
    s3.save()
    progress_report = ProgressReportForDiplomas()
    qs = progress_report.get_queryset().filter(branch_id=branch_spb.pk)
    progress_report = progress_report.generate(qs)
    assert len(progress_report) == 2
    progress_report = ProgressReportForDiplomas()
    qs = progress_report.get_queryset().filter(branch_id=branch_nsk.pk)
    progress_report = progress_report.generate(qs)
    assert len(progress_report) == 1
    assert progress_report.index[0] == s3.pk
