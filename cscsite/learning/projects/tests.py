# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

import pytest
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_bytes
from django.utils.timezone import now

from learning.factories import SemesterFactory
from learning.projects.factories import ProjectFactory, ReportFactory
from learning.projects.models import Report, ProjectStudent
from learning.settings import GRADES, STUDENT_STATUS, PARTICIPANT_GROUPS
from learning.utils import get_current_semester_pair
from notifications.models import Notification
from users.factories import StudentCenterFactory, ProjectReviewerFactory, \
    UserFactory

URL_REVIEWER_PROJECTS = reverse("projects:reviewer_projects")


@pytest.mark.django_db
def test_user_detail(client, student_center_factory):
    """
    Students should have `projects` in their info on profile page.

    Just a simple test to check something appears.
    """
    student = student_center_factory(enrollment_year='2013')
    semester1 = SemesterFactory.create(year=2014, type='spring')
    semester2 = SemesterFactory.create(year=2014, type='autumn')
    p1 = ProjectFactory.create(students=[student], semester=semester1)
    p2 = ProjectFactory.create(students=[student],
                               semester=semester2,
                               description="")
    sp2 = p2.projectstudent_set.all()[0]
    sp2.final_grade = GRADES.good
    sp2.save()
    resp = client.get(reverse('user_detail', args=[student.pk]))
    assert smart_bytes(p1.name) in resp.content
    assert smart_bytes(p1.description) in resp.content
    assert smart_bytes(p2.name) in resp.content
    assert smart_bytes(sp2.get_final_grade_display().lower()) in resp.content


@pytest.mark.django_db
def test_staff_diplomas_view(curator, client, student_center_factory):
    student = student_center_factory(enrollment_year='2013',
                                     status=STUDENT_STATUS.will_graduate)
    semester1 = SemesterFactory.create(year=2014, type='spring')
    p = ProjectFactory.create(students=[student], semester=semester1)
    sp = p.projectstudent_set.all()[0]
    sp.final_grade = GRADES.good
    sp.save()
    client.login(curator)
    response = client.get(reverse('staff:exports_students_diplomas'))
    assert smart_bytes(p.name) in response.content


@pytest.mark.django_db
def test_reviewer_list_security(client,
                                student_center_factory,
                                user_factory,
                                curator):
    """Check ProjectReviewerOnlyMixin"""
    url = "{}?show=reports".format(URL_REVIEWER_PROJECTS)
    response = client.get(url)
    assert response.status_code == 302
    student = student_center_factory()
    client.login(student)
    response = client.get(url)
    assert response.status_code == 302
    reviewer = user_factory.create(groups=[PARTICIPANT_GROUPS.PROJECT_REVIEWER])
    client.login(reviewer)
    response = client.get(url)
    assert response.status_code == 200
    assert not response.context["projects"]
    client.login(curator)
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_reviewer_list(client, user_factory, curator, student_center_factory):
    """Test GET-filter `show` works"""
    url_reports = "{}?show=reports".format(URL_REVIEWER_PROJECTS)
    url_available = "{}?show=available".format(URL_REVIEWER_PROJECTS)
    url_all = "{}?show=all".format(URL_REVIEWER_PROJECTS)
    reviewer = user_factory.create(groups=[PARTICIPANT_GROUPS.PROJECT_REVIEWER])
    year, term_type = get_current_semester_pair()
    semester = SemesterFactory(year=year, type=term_type)
    semester_prev = SemesterFactory(year=year - 1, type=term_type)
    client.login(reviewer)
    student = student_center_factory()
    response = client.get(url_reports)
    assert response.status_code == 200
    assert len(response.context["projects"]) == 0
    # Enroll on project from prev term
    project = ProjectFactory(students=[student], reviewers=[reviewer],
                             semester=semester_prev)
    response = client.get(url_reports)
    assert response.status_code == 200
    assert len(response.context["projects"]) == 0
    # Enroll on project from current term
    ProjectFactory.create(students=[student], reviewers=[reviewer],
                          semester=semester)
    response = client.get(url_reports)
    assert len(response.context["projects"]) == 1
    # With ?show=available filter show projects from current term to reviewers
    response = client.get(url_available)
    assert len(response.context["projects"]) == 1
    client.login(curator)
    response = client.get(url_reports)
    assert len(response.context["projects"]) == 0
    response = client.get(url_available)
    assert len(response.context["projects"]) == 1
    response = client.get(url_all)
    assert len(response.context["projects"]) == 2


@pytest.mark.django_db
def test_create_project_presentations(client):
    """
    Test path to presentation file is with valid project id.

    Let's check it due to Django upload files before model creation.
    """
    from django.core.files.base import ContentFile
    semester = SemesterFactory()
    project = ProjectFactory.build(semester=semester)
    project.presentation = ContentFile("stub", name="test.txt")
    project.supervisor_presentation = ContentFile("stub", name="test.txt")
    project.save()
    assert "None" not in project.presentation.name
    assert "None" not in project.supervisor_presentation.name


@pytest.mark.django_db
def test_project_detail_unauth(client):
    """Make sure unauth user never see report form with any status"""
    student = StudentCenterFactory()
    year, term_type = get_current_semester_pair()
    semester = SemesterFactory(year=year, type=term_type)
    reviewer = ProjectReviewerFactory()
    project = ProjectFactory.create(students=[student], reviewers=[reviewer],
                                    semester=semester)
    response = client.get(project.get_absolute_url())
    assert smart_bytes("Отзывы руководителя") not in response.content
    assert smart_bytes("Следить за проектом") not in response.content
    assert "can_enroll" in response.context
    assert response.context["can_enroll"] is False
    assert "can_send_report" in response.context
    assert response.context["can_send_report"] is False
    assert "can_view_report" in response.context
    assert response.context["can_view_report"] is False
    assert "you_enrolled" in response.context
    assert response.context["you_enrolled"] is False
    # Try to send form with report
    form = {"text": "report text content"}
    response = client.post(project.get_absolute_url(), form)
    assert response.status_code == 403  # Not student participant


@pytest.mark.django_db
def test_project_detail_student_participant(client):
    from datetime import timedelta
    student = StudentCenterFactory()
    year, term_type = get_current_semester_pair()
    semester = SemesterFactory(year=year, type=term_type)
    semester_prev = SemesterFactory(year=year - 1, type=term_type)
    reviewer = ProjectReviewerFactory()
    project = ProjectFactory.create(students=[student], reviewers=[reviewer],
                                    semester=semester)
    client.login(student)
    response = client.get(project.get_absolute_url())
    assert "can_enroll" in response.context
    assert response.context["can_enroll"] is False
    assert smart_bytes("Отзывы руководителя") not in response.content
    form = {"send_report_form-text": "report text content"}
    response = client.post(project.get_absolute_url(), form)
    assert response.status_code == 403  # not active period for sending reports
    today = now().date()
    semester.report_starts_at = today + timedelta(days=2)
    semester.save()
    # Too early to send reports
    response = client.post(project.get_absolute_url(), form)
    assert response.status_code == 403
    semester.report_starts_at = today - timedelta(days=7)
    semester.report_ends_at = today - timedelta(days=2)
    semester.save()
    # Sending period ended
    response = client.post(project.get_absolute_url(), form)
    assert response.status_code == 403
    # Project already stale
    project.semester = semester_prev
    project.save()
    response = client.post(project.get_absolute_url(), form)
    assert response.status_code == 403
    # Ok
    project.semester = semester
    project.save()
    semester.report_starts_at = today
    semester.report_ends_at = today + timedelta(days=1)
    semester.save()
    response = client.post(project.get_absolute_url(), form, follow=True)
    assert response.status_code == 200
    assert Report.objects.count() == 1
    response = client.get(project.get_absolute_url())
    assert response.status_code == 302
    # Test sending form visibility based on sending period activity
    Report.objects.get_queryset().delete()  # delete reports to skip redirect
    response = client.get(project.get_absolute_url())
    assert response.status_code == 200
    assert "can_send_report" in response.context
    assert response.context["can_send_report"] is True
    project.semester = semester_prev
    project.save()
    response = client.get(project.get_absolute_url())
    assert response.context["can_send_report"] is False
    project.semester = semester
    project.save()
    semester.report_starts_at = None
    semester.report_ends_at = None
    semester.save()
    response = client.get(project.get_absolute_url())
    assert response.context["can_send_report"] is False


@pytest.mark.django_db
def test_project_detail_student_participant_notifications(client, curator):
    """Test notifications are added to the queue after report has been sent"""
    from datetime import timedelta
    curator.groups.add(PARTICIPANT_GROUPS.PROJECT_REVIEWER)
    curator.save()
    # This curator not in reviewers group and doesn't receive notifications
    curator2 = UserFactory(is_superuser=True, is_staff=True)
    today = now().date()
    student = StudentCenterFactory()
    year, term_type = get_current_semester_pair()
    semester = SemesterFactory(year=year, type=term_type)
    semester.report_starts_at = today
    semester.report_ends_at = today + timedelta(days=1)
    semester.save()
    reviewer = ProjectReviewerFactory()
    project = ProjectFactory.create(students=[student], reviewers=[reviewer],
                                    semester=semester)
    client.login(student)
    form = {"send_report_form-text": "report text content"}
    response = client.post(project.get_absolute_url(), form)
    assert response.status_code == 302
    assert Notification.objects.count() == 1


@pytest.mark.django_db
def test_project_detail_reviewer(client, curator):
    reviewer = ProjectReviewerFactory()
    client.login(reviewer)
    year, term_type = get_current_semester_pair()
    semester = SemesterFactory(year=year, type=term_type)
    semester_prev = SemesterFactory(year=year - 1, type=term_type)
    student = StudentCenterFactory()
    project = ProjectFactory(students=[student], semester=semester_prev)
    url = project.get_absolute_url()
    response = client.get(url)
    # hide enrollment button for past projects
    assert "can_enroll" in response.context
    assert response.context["can_enroll"] is False
    current_project = ProjectFactory(students=[student], semester=semester)
    url = reverse("projects:project_detail",
                  args=[current_project.pk])
    response = client.get(url)
    assert response.context["can_enroll"] is True
    assert smart_bytes("Смотреть отчет") not in response.content
    # Also, hide button for already enrolled projects
    current_project.reviewers.add(reviewer)
    current_project.save()
    response = client.get(url)
    assert response.context["can_enroll"] is False
    assert smart_bytes("Следить за проектом") not in response.content
    # Don't show testimonials and grade tables to reviewer or students
    assert smart_bytes("Отзывы руководителя") not in response.content
    client.login(curator)
    response = client.get(url)
    assert smart_bytes("Отзывы руководителя") in response.content


@pytest.mark.django_db
def test_reviewer_project_enroll(client, curator):
    year, term_type = get_current_semester_pair()
    semester = SemesterFactory(year=year, type=term_type)
    semester_prev = SemesterFactory(year=year - 1, type=term_type)
    student = StudentCenterFactory()
    old_project = ProjectFactory(students=[student], semester=semester_prev)
    url_for_old = reverse("projects:reviewer_project_enroll",
                          args=[old_project.pk])
    reviewer = ProjectReviewerFactory()
    reviewer2 = ProjectReviewerFactory()
    client.login(reviewer)
    response = client.post(url_for_old, {})
    assert response.status_code == 403
    active_project = ProjectFactory(students=[student], semester=semester)
    urL_for_active = reverse("projects:reviewer_project_enroll",
                             args=[active_project.pk])
    response = client.post(urL_for_active, {}, follow=True)
    assert response.status_code == 200
    assert len(active_project.reviewers.all()) == 1
    assert reviewer in active_project.reviewers.all()
    assert reviewer2 not in active_project.reviewers.all()


@pytest.mark.django_db
def test_report_page_permissions(client, curator):
    reviewer_participant = ProjectReviewerFactory()
    reviewer = ProjectReviewerFactory()
    report = ReportFactory()
    report.project_student.project.reviewers.add(reviewer_participant)
    report.project_student.project.save()
    # Rewrite unauth to login page
    response = client.get(report.get_absolute_url())
    assert response.status_code == 302
    client.login(reviewer)
    response = client.get(report.get_absolute_url())
    assert response.status_code == 302
    client.login(reviewer_participant)
    # Report is in `sent` status, so participant reviewer has no permissions yet
    response = client.get(report.get_absolute_url())
    assert response.status_code == 302
    report.status = Report.REVIEW
    report.save()
    response = client.get(report.get_absolute_url())
    assert response.status_code == 200
    # Login as author of report
    client.login(report.project_student.student)
    response = client.get(report.get_absolute_url())
    assert response.status_code == 200
    # Login as student, but not participant of review
    student = StudentCenterFactory()
    client.login(student)
    response = client.get(report.get_absolute_url())
    assert response.status_code == 302
    # Add student to project participants, but he's still should be redirected
    ps = ProjectStudent(project=report.project_student.project, student=student)
    ps.save()
    assert ProjectStudent.objects.count() == 2
    response = client.get(report.get_absolute_url())
    assert response.status_code == 302

# TODO: простой тест о том, что обновлять статус может только куратор (чекать, что добавлен mixin? вроде это самый простой вариант)
# TODO: нельзя писать комменты, если проект уже не активен (прочекать состояния в зависимости от статуса отчета)
# TODO: нотификации добавляются при отправке комментов и нужным людям.

# TODO: проверить видимость форм, на уровне контекста, post-запросы
# TODO: прочекать средний балл.
