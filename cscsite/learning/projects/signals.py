# -*- coding: utf-8 -*-

from django.apps import apps
from django.contrib.auth import get_user_model

from learning.settings import PARTICIPANT_GROUPS
from notifications.signals import notify

_UNSAVED_FILE_SUPERVISOR_PRESENTATION = 'unsaved_supervisor_presentation'
_UNSAVED_FILE_PRESENTATION = 'unsaved_presentation'


def pre_save_project(sender, instance, **kwargs):
    """
    Save presentation files when project model already created and we can
    get project pk.
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


def post_save_project(sender, instance, created, *args, **kwargs):
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
            instance.save()


# TODO: add tests
def post_save_report(sender, instance, created, *args, **kwargs):
    """ Send notifications to curators by email about new report"""
    # FIXME: Looks like you need send emails to reviewers!
    if created:
        report = instance
        CSCUser = get_user_model()
        if report.status == report.SENT:
            # Send email to appropriate curators
            curators = CSCUser.objects.filter(
                is_superuser=True,
                is_staff=True,
                groups=PARTICIPANT_GROUPS.PROJECT_REVIEWER
            )
            for curator in curators:
                notify.send(
                    report.project_student.student,
                    verb='added',
                    description="new report added",
                    action_object=report,
                    recipient=curator
                )


def post_save_review(sender, instance, created, *args, **kwargs):
    """Update report status if all reviews are completed."""
    review = instance
    report = review.report
    Report = apps.get_model('projects', 'Report')
    if review.is_completed:
        total_reviewers = len(report.project_student.project.reviewers.all())
        completed_reviews = sum(r.is_completed for r in report.review_set.all())
        if completed_reviews == total_reviewers:
            report.status = Report.RATING
            # TODO: Mb send notification to curators?
            report.save()


# TODO: add tests
def post_save_comment(sender, instance, created, *args, **kwargs):
    """Add notification when report comment has been created."""
    if created:
        comment = instance
        reviewers = comment.report.project_student.project.reviewers.all()
        recipients = [r for r in reviewers if r != comment.author]
        if comment.author != comment.report.project_student.student:
            recipients.append(comment.report.project_student.student)
        for recipient in recipients:
            notify.send(
                comment.author,  # actor
                verb='added',
                description="new comment added",
                action_object=comment,
                target=comment.report,
                recipient=recipient)
