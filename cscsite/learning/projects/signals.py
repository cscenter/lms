# -*- coding: utf-8 -*-
from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from learning.projects.models import ProjectStudent, Report, Project, Review, \
    ReportComment
from learning.settings import PARTICIPANT_GROUPS
from notifications import types
from notifications.signals import notify

_UNSAVED_FILE_SUPERVISOR_PRESENTATION = 'unsaved_supervisor_presentation'
_UNSAVED_FILE_PRESENTATION = 'unsaved_presentation'


@receiver(pre_save, sender=Project)
def pre_save_project(sender, instance, **kwargs):
    """
    Save presentation files after project created and we can get project pk.
    """
    if not instance.pk:
        if not hasattr(instance, _UNSAVED_FILE_SUPERVISOR_PRESENTATION):
            setattr(instance, _UNSAVED_FILE_SUPERVISOR_PRESENTATION,
                    instance.supervisor_presentation)
            instance.supervisor_presentation = None
        if not hasattr(instance, _UNSAVED_FILE_PRESENTATION):
            setattr(instance, _UNSAVED_FILE_PRESENTATION,
                    instance.presentation)
            instance.presentation = None


@receiver(post_save, sender=ProjectStudent)
def post_save_project_student(sender, instance, *args, **kwargs):
    """
    Auto cancel project if all participants leave it without reporting.
    All participants should have `unsatisfactory` grade in that case.
    """
    project_student = instance
    project_id = project_student.project_id
    project_students = (ProjectStudent.objects
                        .filter(project=project_id)
                        .select_related("report"))
    all_left_project = True
    for ps in project_students:
        try:
            # Skip if any participant has report
            _ = ps.report.pk
            all_left_project = False
            break
        except ObjectDoesNotExist:
            pass
        # Or has any positive/neutral grade
        if ps.final_grade != ProjectStudent.GRADES.unsatisfactory:
            all_left_project = False
            break
    Project.objects.filter(pk=project_id).update(canceled=all_left_project)


@receiver(post_save, sender=Project)
def post_save_project(sender, instance, created, *args, **kwargs):
    from learning.projects.tasks import (
        download_presentation_from_yandex_disk_supervisor as job_ya_supervisor,
        download_presentation_from_yandex_disk_students as job_ya_students)
    if created:
        save = False
        if hasattr(instance, _UNSAVED_FILE_SUPERVISOR_PRESENTATION):
            instance.supervisor_presentation = getattr(
                instance,
                _UNSAVED_FILE_SUPERVISOR_PRESENTATION
            )
            instance.__dict__.pop(_UNSAVED_FILE_SUPERVISOR_PRESENTATION)
            save = True
        if hasattr(instance, _UNSAVED_FILE_PRESENTATION):
            instance.presentation = getattr(instance,
                                            _UNSAVED_FILE_PRESENTATION)
            instance.__dict__.pop(_UNSAVED_FILE_PRESENTATION)
            save = True
        if save:
            # post save signal will be resend here
            instance.save()
            return

    # Download presentation from yandex.disk if local copy not saved.
    if (instance.supervisor_presentation_url and
            instance.supervisor_presentation == ''):
        transaction.on_commit(lambda: job_ya_supervisor.delay(instance.pk))
    # Same logic for participants presentation
    if instance.presentation_url and instance.presentation == '':
        transaction.on_commit(lambda: job_ya_students.delay(instance.pk))


@receiver(post_save, sender=Report)
def post_save_report(sender, instance, created, *args, **kwargs):
    """ Send notifications to curators by email about new report"""
    if created:
        report = instance
        User = get_user_model()
        if report.status == report.SENT:
            # Send email to curators
            recipients = User.objects.filter(
                is_superuser=True,
                is_staff=True,
                groups=PARTICIPANT_GROUPS.CURATOR_PROJECTS
            )
            # TODO: test database hitting
            project = report.project_student.project
            student = report.project_student.student
            for recipient in recipients:
                notify.send(
                    report.project_student.student,  # actor
                    type=types.NEW_PROJECT_REPORT,
                    verb='sent',
                    action_object=report,
                    target=report.project_student.project,
                    recipient=recipient,
                    # Unmodified context
                    data={
                        "project_name": project.name,
                        "project_pk": project.pk,
                        "student_pk": student.pk,
                    }
                )


@receiver(post_save, sender=Review)
def post_save_review(sender, instance, created, *args, **kwargs):
    """Update report status if all reviews are completed."""
    review = instance
    report = review.report
    Report = apps.get_model('projects', 'Report')
    if review.is_completed:
        total_reviewers = len(report.project_student.project.reviewers.all())
        completed_reviews = sum(r.is_completed for r in report.review_set.all())
        if completed_reviews == total_reviewers:
            report.status = Report.SUMMARY
            report.save()


@receiver(post_save, sender=ReportComment)
def post_save_comment(sender, instance, created, *args, **kwargs):
    """Add notification when report comment has been created."""
    if created:
        Report = apps.get_model('projects', 'Report')
        User = get_user_model()
        comment = instance
        curators = (User.objects
                    .filter(
                        is_superuser=True,
                        is_staff=True,
                        groups=PARTICIPANT_GROUPS.CURATOR_PROJECTS)
                    .exclude(pk=comment.author.pk))
        # Make dict to avoid duplicates
        recipients = {c.pk: c for c in curators}
        student = comment.report.project_student.student
        if comment.author != student:
            recipients[student.pk] = comment.report.project_student.student
        if comment.report.status == Report.REVIEW:
            reviewers = comment.report.project_student.project.reviewers.all()
            recipients.update({r.pk: r for r in reviewers if r != comment.author})
        # Note: Doesn't hit database here if relations already cached
        project = comment.report.project_student.project
        student = comment.report.project_student.student

        for recipient in recipients.values():
            notify.send(
                comment.author,  # actor
                type=types.NEW_PROJECT_REPORT_COMMENT,
                verb='added',
                action_object=comment,
                target=comment.report,
                recipient=recipient,
                data={
                    "student_id": student.pk,
                    "project_name": project.name,
                    "project_pk": project.pk,  # unmodified
                    "student_pk": student.pk,  # unmodified
                }
            )
