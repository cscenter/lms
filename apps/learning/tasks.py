import logging
import os

from django_rq import job

from files.utils import convert_ipynb_to_html
from learning.models import AssignmentComment, StudentAssignment, SubmissionAttachment
from learning.services.notification_service import (
    create_notifications_about_new_submission
)
from learning.services.personal_assignment_service import (
    update_personal_assignment_stats, maybe_set_assignee_for_personal_assignment
)

logger = logging.getLogger(__file__)


@job('default')
def convert_assignment_submission_ipynb_file_to_html(*, assignment_submission_id):
    try:
        submission = AssignmentComment.objects.get(pk=assignment_submission_id)
    except AssignmentComment.DoesNotExist:
        logger.debug(f"Submission with id={assignment_submission_id} not found")
        return
    # Have to take only name of file
    original_file_name = os.path.splitext(os.path.basename(submission.attached_file.name))[0]
    file_name = original_file_name + '.html'
    # Actually it could be any file with the same name
    file_field = SubmissionAttachment._meta.get_field('attachment')
    if file_field.storage.exists(file_name):
        return
    html_source = convert_ipynb_to_html(submission.attached_file,
                                        name=file_name)
    if html_source is None:
        logger.debug("File not converted")
        return
    SubmissionAttachment.objects.create(submission=submission,
                                        attachment=html_source)


@job('default')
def update_student_assignment_stats(student_assignment_id: int) -> None:
    student_assignment = (StudentAssignment.objects
                          .filter(pk=student_assignment_id)
                          .first())
    if not student_assignment:
        return
    update_personal_assignment_stats(personal_assignment=student_assignment)


@job('high')
def handle_submission_assignee_and_notifications(assignment_submission_id: int):
    maybe_set_assignee_for_personal_assignment(assignment_submission_id)
    # P.S. Moved from AssignmentComment.save(): FIXME: add transaction.on_commit()
    generate_notifications_about_new_submission.delay(assignment_submission_id=assignment_submission_id)


@job('high')
def generate_notifications_about_new_submission(*, assignment_submission_id):
        # Do not need to make notifications if student_assignment is not active
    try:
        submission = (AssignmentComment.objects
                      .select_related('student_assignment__assignment',
                                      'student_assignment__assignee')
                      .only('id', 'type', 'is_published', 'author_id',
                            'student_assignment_id',
                            'student_assignment__assignment__course_id',
                            'student_assignment__student_id',
                            'student_assignment__assignee__teacher_id')
                      .order_by()
                      .get(pk=assignment_submission_id))
    except AssignmentComment.DoesNotExist:
        logger.debug(f"Submission with id={assignment_submission_id} not found")
        return
    if not StudentAssignment.objects.active().filter(pk=submission.student_assignment.pk).exists():
        logger.debug(f"Submission with id={assignment_submission_id} is not active")
        return
    count = create_notifications_about_new_submission(submission)
    return f'Generated {count} notifications'
