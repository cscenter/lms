import logging
from typing import Optional

from django_rq import job

from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from auth.models import ConnectedAuthService
from code_reviews.api.gerrit import Gerrit
from code_reviews.api.ldap import ldap_client
from code_reviews.gerrit.ldap_service import (
    get_ldap_username, update_ldap_user_password_hash, connect_gerrit_auth_provider
)
from code_reviews.gerrit.services import (
    get_or_create_change, list_change_files, normalize_code_review_score, get_reviewers_group_name,
    add_student_to_project
)
from code_reviews.models import GerritChange
from courses.constants import AssignmentStatus
from courses.models import Course
from learning.models import AssignmentComment, AssignmentSubmissionTypes, Enrollment
from learning.permissions import EditStudentAssignment
from learning.services.personal_assignment_service import (
    create_personal_assignment_review
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

    # Old score value from Gerrit is not actually used.
    score_old = student_assignment.score
    gerrit_score = normalize_code_review_score(score_new, assignment)
    if gerrit_score == assignment.maximum_score:
        status_new = AssignmentStatus.COMPLETED
        score_new = gerrit_score
    else:
        status_new = AssignmentStatus.NEED_FIXES
        score_new = student_assignment.score

    logger.info(f"Posting score {score_old} -> {score_new} for personal "
                f"assignment {student_assignment.pk}")

    # Check site permissions of the main branch of the course
    access_groups = changed_by.get_site_groups(assignment.course.main_branch.site_id)
    changed_by.roles = {g.role for g in access_groups}
    if not changed_by.has_perm(EditStudentAssignment.name, student_assignment):
        logger.error(f"User {changed_by.pk} has no permission to "
                     f"edit student assignment {student_assignment.pk}")
        return None

    with transaction.atomic():
        create_personal_assignment_review(student_assignment=student_assignment,
                                          reviewer=changed_by,
                                          is_draft=False,
                                          score_old=student_assignment.score,
                                          score_new=score_new,
                                          status_old=student_assignment.status,
                                          status_new=status_new,
                                          message=_("Update in Gerrit"),
                                          source=AssignmentScoreUpdateSource.WEBHOOK_GERRIT)
    return student_assignment.pk


@job('default')
def add_student_to_gerrit_project(enrollment: Enrollment):
    gerrit_client = Gerrit(settings.GERRIT_API_URI,
                           auth=(settings.GERRIT_CLIENT_USERNAME,
                                 settings.GERRIT_CLIENT_HTTP_PASSWORD))
    with ldap_client() as client:
        course = enrollment.course
        connect_gerrit_auth_provider(client, enrollment.student)
        add_student_to_project(gerrit_client=gerrit_client,
                               ldap_client=client,
                               student_profile=enrollment.student_profile,
                               course=course)


@job('default')
def add_teacher_to_gerrit_project(course: Course, teacher: settings.AUTH_USER_MODEL):
    gerrit_client = Gerrit(settings.GERRIT_API_URI,
                           auth=(settings.GERRIT_CLIENT_USERNAME,
                                 settings.GERRIT_CLIENT_HTTP_PASSWORD))
    with ldap_client() as client:
        connect_gerrit_auth_provider(client, teacher)
    reviewers_group_name = get_reviewers_group_name(course)
    reviewers_group_res = gerrit_client.get_group(reviewers_group_name)
    reviewers_group_uuid = reviewers_group_res.data["id"]
    teacher_login = get_ldap_username(teacher)
    gerrit_client.create_group_member(reviewers_group_uuid, teacher_login)
