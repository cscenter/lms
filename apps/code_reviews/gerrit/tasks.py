import logging
from typing import Optional

from django_rq import job

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from auth.models import ConnectedAuthService
from code_reviews.api.gerrit import Gerrit
from code_reviews.api.ldap import ldap_client
from code_reviews.gerrit.ldap_service import (
    get_ldap_username, update_ldap_user_password_hash
)
from code_reviews.gerrit.services import (
    get_or_create_change, list_change_files, normalize_code_review_score
)
from code_reviews.models import GerritChange
from courses.constants import AssignmentStatus
from learning.models import AssignmentComment, AssignmentSubmissionTypes
from learning.permissions import EditStudentAssignment
from learning.services.personal_assignment_service import (
    update_personal_assignment_score, update_personal_assignment_status
)
from learning.settings import AssignmentScoreUpdateSource
from users.models import User

logger = logging.getLogger(__name__)


@job('high')
def update_password_in_gerrit(*, user_id: int):
    """Updates LDAP password hash in Gerrit."""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning(f"User with id={user_id} not found")
        return
    with ldap_client() as client:
        uid = get_ldap_username(user)
        if not client.search_users(uid):
            # User doesn't exist
            return
        updated = update_ldap_user_password_hash(client, user)
        if not updated:
            logger.error(f"Password hash for user {user_id} wasn't changed")


@job('default')
def upload_attachment_to_gerrit(assignment_comment_id):
    assignment_solution = (AssignmentComment.objects
                           .select_related('student_assignment')
                           .get(type=AssignmentSubmissionTypes.SOLUTION,
                                pk=assignment_comment_id))
    student_assignment = assignment_solution.student_assignment
    attached_file = assignment_solution.attached_file

    client = Gerrit(settings.GERRIT_API_URI,
                    auth=(settings.GERRIT_CLIENT_USERNAME,
                          settings.GERRIT_CLIENT_HTTP_PASSWORD))

    change = get_or_create_change(client, student_assignment)
    if not change:
        logger.error(f'Failed to get or create a change for '
                     f'personal assignment {student_assignment.pk}')
        return

    # FIXME: Files can only be added to changes that have not been merged into the code base.

    response = client.get_change_edit(change.change_id)
    if not response.no_content:
        logger.info(f'Found previous change edit for the change {change.change_id}')
        response = client.delete_change_edit(change.change_id)
        if not response.no_content:
            logger.error('Failed to delete current change edit')

    # Save extension to enable syntax highlighting in the UI
    extension = attached_file.name.split('.')[-1]
    solution_filename = f"solution.{extension}"

    # Delete other existing files
    change_files = list_change_files(client, change)
    for file in change_files:
        if file != solution_filename:
            client.delete_file(change.change_id, file)

    # Put content of a solution file to a change edit.
    response = client.upload_file(change.change_id, solution_filename,
                                  attached_file)
    # FIXME: When the change edit is a no-op, for example when providing the
    #  same file content that the file already has, '409 no changes were made' is returned.
    if not response.no_content:
        logger.info('Failed to upload the solution')

    # Promotes Change Edit to a regular Patch Set.
    response = client.publish_change_edit(change.change_id)
    if not response.no_content:
        logger.error('Failed to publish change edit')
        return


@job('default')
def import_gerrit_code_review_score(*, change_id: str, score_old: int,
                                    score_new: int, username: str) -> Optional[int]:
    try:
        change = (GerritChange.objects
                  .select_related('student_assignment__assignment__course')
                  .get(change_id=change_id))
        student_assignment = change.student_assignment
    except GerritChange.DoesNotExist:
        logger.error("Change id has not been found.")
        return
    try:
        gerrit_auth = (ConnectedAuthService.objects
                       .select_related('user')
                       .get(provider='gerrit', uid=username))
        changed_by = gerrit_auth.user
    except ConnectedAuthService.DoesNotExist:
        logger.error(f"User account associated with gerrit "
                     f"username {username} has not been found.")
        return

    assignment = student_assignment.assignment
    score_old = normalize_code_review_score(score_old, assignment)
    score_new = normalize_code_review_score(score_new, assignment)

    logger.info(f"Posting score {score_old} -> {score_new} for personal "
                f"assignment {student_assignment.pk}")

    score_current = student_assignment.score
    if score_current is not None and score_current != score_old:
        # FIXME: log warning instead after score update logging will be implemented
        raise ValidationError("Abort operation since current score value "
                              "differs from the expected.")

    # Cast Gerrit webhook value to None if it's the first score update.
    if not score_old and not score_current:
        score_old = score_current

    # Check site permissions of the main branch of the course
    access_groups = changed_by.get_site_groups(assignment.course.main_branch.site_id)
    changed_by.roles = {g.role for g in access_groups}
    if not changed_by.has_perm(EditStudentAssignment.name, student_assignment):
        logger.error(f"User {changed_by.pk} has no permission to "
                     f"edit student assignment {student_assignment.pk}")
        return None

    with transaction.atomic():
        update_personal_assignment_score(student_assignment=student_assignment,
                                         changed_by=changed_by,
                                         score_old=score_old,
                                         score_new=score_new,
                                         source=AssignmentScoreUpdateSource.WEBHOOK_GERRIT)
        status_new = AssignmentStatus.NEED_FIXES
        if score_new == student_assignment.assignment.maximum_score:
            status_new = AssignmentStatus.COMPLETED
        update_personal_assignment_status(student_assignment=student_assignment,
                                          status_old=AssignmentStatus(student_assignment.status),
                                          status_new=status_new)
    return student_assignment.pk
