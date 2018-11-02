# -*- coding: utf-8 -*-

import pytest
from django.urls import reverse
from django.utils.encoding import smart_bytes
from django.utils.timezone import now

from learning.factories import SemesterFactory
from learning.projects.factories import ProjectFactory, ReportFactory, \
    ReportReviewFormFactory
from learning.projects.models import Report, ProjectStudent
from learning.settings import GRADES, AcademicRoles, \
    StudentStatuses
from learning.utils import get_current_term_pair
from notifications.models import Notification
from users.factories import StudentCenterFactory, ProjectReviewerFactory, \
    UserFactory, CuratorFactory

URL_REPORTS = reverse("projects:report_list_reviewers")
URL_PROJECTS = reverse("projects:current_term_projects")
URL_ALL_PROJECTS = reverse("projects:all_projects")


@pytest.mark.django_db
def test_user_detail(client):
    """
    Students should have `projects` in their info on profile page.

    Just a simple test to check something appears.
    """
    student = StudentCenterFactory(enrollment_year='2013')
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
    assert smart_bytes(p2.name) in resp.content
    assert smart_bytes(sp2.get_final_grade_display().lower()) in resp.content


@pytest.mark.django_db
def test_staff_diplomas_view(curator, client):
    student = StudentCenterFactory(enrollment_year='2013',
                                   status=StudentStatuses.will_graduate)
    semester1 = SemesterFactory.create(year=2014, type='spring')
    p = ProjectFactory.create(students=[student], semester=semester1)
    sp = p.projectstudent_set.all()[0]
    sp.final_grade = GRADES.good
    sp.save()
    client.login(curator)
    response = client.get(reverse('staff:exports_students_diplomas_tex',
                                  kwargs={"city_code": "spb"}))
    assert smart_bytes(p.name) in response.content


@pytest.mark.django_db
def test_project_reviewer_only_mixin_security(client, curator):
    response = client.get(URL_REPORTS)
    assert response.status_code == 302
    student = StudentCenterFactory()
    client.login(student)
    response = client.get(URL_REPORTS)
    assert response.status_code == 302
    reviewer = UserFactory.create(groups=[AcademicRoles.PROJECT_REVIEWER])
    client.login(reviewer)
    response = client.get(URL_REPORTS)
    assert response.status_code == 200
    assert not response.context["projects"]
    client.login(curator)
    response = client.get(URL_REPORTS, follow=True)
    # Redirects to reports-all page
    assert response.status_code == 200


@pytest.mark.django_db
def test_reviewer_list(client, curator):
    """Test GET-filter `show` works"""
    reviewer = ProjectReviewerFactory.create()
    year, term_type = get_current_term_pair('spb')
    semester = SemesterFactory(year=year, type=term_type)
    semester_prev = SemesterFactory(year=year - 1, type=term_type)
    client.login(reviewer)
    student = StudentCenterFactory()
    response = client.get(URL_REPORTS)
    assert response.status_code == 200
    assert len(response.context["projects"]) == 0
    # Enroll on project from prev term
    project = ProjectFactory(students=[student], reviewers=[reviewer],
                             semester=semester_prev)
    response = client.get(URL_REPORTS)
    assert response.status_code == 200
    assert len(response.context["projects"]) == 0
    # Enroll on project from current term
    ProjectFactory.create(students=[student], reviewers=[reviewer],
                          semester=semester)
    response = client.get(URL_REPORTS)
    assert len(response.context["projects"]) == 1
    # With ?show=available filter show projects from current term to reviewers
    response = client.get(URL_PROJECTS)
    assert len(response.context["projects"]) == 1
    curator.groups.add(AcademicRoles.PROJECT_REVIEWER)
    client.login(curator)
    # Redirects to list with all reports
    response = client.get(URL_REPORTS, follow=True)
    assert len(response.context["projects"]) == 1
    response = client.get(URL_PROJECTS)
    assert len(response.context["projects"]) == 1
    response = client.get(URL_ALL_PROJECTS)
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
    year, term_type = get_current_term_pair('spb')
    semester = SemesterFactory(year=year, type=term_type)
    reviewer = ProjectReviewerFactory()
    project = ProjectFactory.create(students=[student], reviewers=[reviewer],
                                    semester=semester)
    response = client.get(project.get_absolute_url())
    assert smart_bytes("Отзывы руководителей") not in response.content
    assert smart_bytes("Следить за проектом") not in response.content
    assert "can_enroll" in response.context
    assert response.context["can_enroll"] is False
    assert "has_send_permissions" in response.context
    assert response.context["has_send_permissions"] is False
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
    year, term_type = get_current_term_pair('spb')
    semester = SemesterFactory(year=year, type=term_type)
    semester_prev = SemesterFactory(year=year - 1, type=term_type)
    reviewer = ProjectReviewerFactory()
    project = ProjectFactory.create(students=[student], reviewers=[reviewer],
                                    semester=semester)
    client.login(student)
    response = client.get(project.get_absolute_url())
    assert "can_enroll" in response.context
    assert response.context["can_enroll"] is False
    assert smart_bytes("Отзывы руководителей") not in response.content
    form = {"send_report_form-text": "report text content"}
    today = now().date()
    semester.report_starts_at = today + timedelta(days=2)
    semester.save()
    # Too early to send reports
    response = client.post(project.get_absolute_url(), form)
    assert response.status_code == 403
    # Project already stale
    project.semester = semester_prev
    project.save()
    response = client.post(project.get_absolute_url(), form)
    assert response.status_code == 403
    # Sending period ended, but they are still can send reports
    project.semester = semester
    project.save()
    semester.report_starts_at = today - timedelta(days=7)
    semester.report_ends_at = today - timedelta(days=2)
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
    assert "has_send_permissions" in response.context
    assert response.context["has_send_permissions"] is True
    project.semester = semester_prev
    project.save()
    response = client.get(project.get_absolute_url())
    assert response.context["has_send_permissions"] is True
    assert project.is_active() is False
    project.semester = semester
    project.save()
    # If report_starts_at not specified, allow sending report while project
    # is active
    semester.report_starts_at = None
    semester.report_ends_at = None
    semester.save()
    response = client.get(project.get_absolute_url())
    assert response.context["has_send_permissions"] is True


@pytest.mark.django_db
def test_project_detail_student_participant_notifications(client, curator):
    """Test notifications are added to the queue after report has been sent"""
    from datetime import timedelta
    curator.groups.add(AcademicRoles.CURATOR_PROJECTS)
    curator.save()
    # This curator not in reviewers group and doesn't receive notifications
    curator2 = UserFactory(is_superuser=True, is_staff=True)
    today = now().date()
    student = StudentCenterFactory(city_id='spb')
    year, term_type = get_current_term_pair('spb')
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
    year, term_type = get_current_term_pair('spb')
    semester = SemesterFactory(year=year, type=term_type)
    semester_prev = SemesterFactory(year=year - 1, type=term_type)
    student = StudentCenterFactory(city_id='spb')
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
    assert smart_bytes("Следить за проектом") not in response.content
    # Don't show testimonials and grade tables to reviewer or students
    assert smart_bytes("Отзывы руководителей") not in response.content
    client.login(curator)
    response = client.get(url)
    assert smart_bytes("Отзывы руководителей") in response.content


@pytest.mark.django_db
def test_reviewer_project_enroll(client, curator):
    year, term_type = get_current_term_pair('spb')
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
    url_enroll_in_active = reverse("projects:reviewer_project_enroll",
                                   args=[active_project.pk])
    response = client.post(url_enroll_in_active, {}, follow=True)
    assert response.status_code == 200
    assert len(active_project.reviewers.all()) == 1
    assert reviewer in active_project.reviewers.all()
    assert reviewer2 not in active_project.reviewers.all()
    # Curator has no reviewers group, but it's ok
    client.login(curator)
    response = client.post(url_enroll_in_active, {}, follow=True)
    assert response.status_code == 200


@pytest.mark.django_db
def test_reportpage_permissions(client, curator):
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


@pytest.mark.django_db
def test_reportpage_update_permissions():
    """Check report updating restricted to curators only"""
    from learning.projects.views import (ReportUpdateStatusView,
        ReportCuratorAssessmentView)
    from learning.viewmixins import CuratorOnlyMixin
    assert issubclass(ReportCuratorAssessmentView, CuratorOnlyMixin)
    assert issubclass(ReportUpdateStatusView, CuratorOnlyMixin)


@pytest.mark.django_db
def test_reportpage_notifications(client, curator):
    curator.groups.add(AcademicRoles.CURATOR_PROJECTS)
    curator2 = CuratorFactory.create()
    reviewer1, reviewer2 = ProjectReviewerFactory.create_batch(2)
    client.login(reviewer1)
    year, term_type = get_current_term_pair('spb')
    semester = SemesterFactory(year=year, type=term_type)
    student1, student2 = StudentCenterFactory.create_batch(2, city_id='spb')
    project = ProjectFactory(students=[student1, student2],
                             semester=semester,
                             reviewers=[reviewer1, reviewer2])
    ps1, _ = ProjectStudent.objects.get_or_create(project=project,
                                                  student=student1)
    report = ReportFactory(project_student=ps1)
    assert report.status == Report.SENT
    assert Notification.objects.count() == 1
    Notification.objects.get_queryset().delete()
    form = {"new_comment_form-text": "test", "new_comment_form": "Save"}
    # Reviewer can't send comments when status is `SENT`
    client.login(reviewer1)
    client.post(report.get_absolute_url(), form)
    assert Notification.objects.count() == 0
    client.login(student1)
    client.post(report.get_absolute_url(), form)
    assert Notification.objects.count() == 1
    assert Notification.objects.all()[0].recipient == curator
    Notification.objects.get_queryset().delete()
    client.login(curator)
    client.post(report.get_absolute_url(), form)
    assert Notification.objects.count() == 1
    assert Notification.objects.all()[0].recipient == student1
    Notification.objects.get_queryset().delete()
    report.status = Report.REVIEW
    report.save()
    client.post(report.get_absolute_url(), form)
    assert Notification.objects.count() == 3
    Notification.objects.get_queryset().delete()
    client.login(student1)
    client.post(report.get_absolute_url(), form)
    assert Notification.objects.count() == 3
    Notification.objects.get_queryset().delete()
    client.login(reviewer1)
    client.post(report.get_absolute_url(), form)
    assert Notification.objects.count() == 3
    recipients = [n.recipient for n in Notification.objects.all()]
    assert reviewer2 in recipients
    assert curator in recipients
    assert student1 in recipients
    Notification.objects.get_queryset().delete()
    # If report is completed, can't send comments
    report.status = Report.COMPLETED
    report.save()
    response = client.post(report.get_absolute_url(), form)
    assert response.status_code == 403
    assert Notification.objects.count() == 0
    # Also, we can't post review
    review_form = ReportReviewFormFactory(report=report, reviewer=reviewer1)
    client.login(reviewer1)
    response = client.post(review_form.send_to, review_form.data)
    assert response.status_code == 403
    # Change report status to send review
    report.status = Report.REVIEW
    report.save()
    response = client.post(review_form.send_to, review_form.data, follow=True)
    assert response.status_code == 200
    # Create report for second student
    ps2, _ = ProjectStudent.objects.get_or_create(project=project,
                                                  student=student2)
    report2 = ReportFactory(project_student=ps2, status=Report.COMPLETED)
    # When we rollback status to `review` stage, make sure notifications
    # won't send to reviewers, who already sent review.
    client.login(curator)
    update_report2_status_url = reverse(
        "projects:project_report_update_status",
        kwargs={
            "student_pk": report2.project_student.student.pk,
            "project_pk": report2.project_student.project.pk,
        })
    client.post(update_report2_status_url, {
        "report_status_change-status": "review",
    })
    assert Notification.objects.count() == 2  # no reviews on report2 yet
    Notification.objects.get_queryset().delete()
    client.login(reviewer2)
    review_form = ReportReviewFormFactory(report=report2, reviewer=reviewer2)
    response = client.post(review_form.send_to, review_form.data)
    # Rollback status again, now we have review on report2
    report2.status = Report.COMPLETED
    report2.save()
    client.login(curator)
    response = client.post(update_report2_status_url, {
        "report_status_change-status": "review",
    }, follow=True)
    assert response.status_code == 200
    assert Notification.objects.count() == 1


@pytest.mark.django_db
def test_reportpage_summarize_notifications(client, curator):
    from learning.viewmixins import CuratorOnlyMixin
    from learning.projects.views import ReportCuratorSummarizeView
    assert issubclass(ReportCuratorSummarizeView, CuratorOnlyMixin)
    curator.groups.add(AcademicRoles.PROJECT_REVIEWER)
    curator2 = CuratorFactory.create()
    reviewer1, reviewer2 = ProjectReviewerFactory.create_batch(2)
    client.login(reviewer1)
    year, term_type = get_current_term_pair('spb')
    semester = SemesterFactory(year=year, type=term_type)
    student1, student2 = StudentCenterFactory.create_batch(2)
    project = ProjectFactory(students=[student1, student2],
                             semester=semester,
                             reviewers=[reviewer1, reviewer2])
    ps1, _ = ProjectStudent.objects.get_or_create(project=project,
                                                  student=student1)
    report = ReportFactory(project_student=ps1)
    report.status = Report.SUMMARY
    report.save()
    client.login(curator)
    form = {
        "report_summary_form": "Save",
        "report_summary_form-final_score_note": "test",
    }
    Notification.objects.get_queryset().delete()
    client.post(report.get_absolute_url(), form)
    assert Notification.objects.count() == 0
    form["report_summary_form-complete"] = "1"
    url = reverse("projects:project_report_summarize", kwargs={
        "student_pk": report.project_student.student.pk,
        "project_pk": report.project_student.project.pk,
    })
    client.post(url, form)
    assert Notification.objects.count() == 1
    assert Notification.objects.all()[0].recipient == student1



# TODO: проверить видимость форм, на уровне контекста, post-запросы
# TODO: test notifications was read on target pages: new comment, new report