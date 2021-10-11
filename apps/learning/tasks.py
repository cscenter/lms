import logging

from django_rq import job

from files.utils import convert_ipynb_to_html
from learning.models import AssignmentComment, StudentAssignment, SubmissionAttachment
from learning.services import (
    create_notifications_about_new_submission, update_personal_assignment_stats
)

logger = logging.getLogger(__file__)


@job('default')
def convert_assignment_submission_ipynb_file_to_html(*, assignment_submission_id):
    try:
        submission = AssignmentComment.objects.get(pk=assignment_submission_id)
    except AssignmentComment.DoesNotExist:
        logger.debug(f"Submission with id={assignment_submission_id} not found")
        return
    file_name = submission.attached_file.name + '.html'
    # Actually it could any file with the same name
    file_field = SubmissionAttachment._meta.get_field('attachment')
    if file_field.storage.exists(file_name):
        return
    html_source = convert_ipynb_to_html(submission.attached_file,
                                        name=file_name)
    if html_source is None:
        logger.debug("File not converted")
        return
    submission_attachment = SubmissionAttachment(submission=submission,
                                                 attachment=html_source)
    submission_attachment.save()


@job('default')
def update_student_assignment_stats(student_assignment_id: int) -> None:
    student_assignment = (StudentAssignment.objects
                          .filter(pk=student_assignment_id)
                          .first())
    if not student_assignment:
        return
    update_personal_assignment_stats(personal_assignment=student_assignment)


@job('high')
def generate_notifications_about_new_submission(*, assignment_submission_id):
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
    count = create_notifications_about_new_submission(submission)
    return f'Generated {count} notifications'
