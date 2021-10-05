import logging
from typing import Optional

from django.conf import settings
from django.db.models import prefetch_related_objects
from django.utils import translation

from code_reviews.api.gerrit import Gerrit
from code_reviews.api.ldap import LDAPClient, init_ldap_connection
from code_reviews.gerrit.constants import GerritRobotMessages
from code_reviews.gerrit.ldap import (
    create_ldap_user, get_ldap_username, update_ldap_user_password_hash
)
from code_reviews.gerrit.permissions import (
    grant_personal_sandbox, grant_reviewers_access, grant_student_access,
    grant_students_read_master
)
from code_reviews.models import GerritChange
from courses.models import Course, CourseTeacher
from courses.services import CourseService
from learning.models import (
    AssignmentComment, AssignmentSubmissionTypes, Enrollment, StudentAssignment
)
from learning.services import StudentGroupService
from users.models import StudentProfile, User

logger = logging.getLogger(__name__)


def get_project_name(course: Course) -> str:
    main_branch = course.main_branch.code
    course_name = course.meta_course.slug.replace("-", "_")
    # TODO: deprecated project name format. Can remove in spring 2022
    if course.pk == 964 or course.semester.year < 2021:
        return f"{main_branch}/{course_name}_{course.semester.year}"
    return CourseService.get_course_uri(course)


def get_branch_name(student_profile: StudentProfile, course: Course) -> str:
    git_branch_name = student_profile.user.get_abbreviated_name_in_latin()
    # FIXME: always attach branch code (unsafe to do it while projects are not fully initialized)
    if len(course.branches.all()) > 1:
        git_branch_name = f"{student_profile.branch.code}/{git_branch_name}"
    return git_branch_name


def get_reviewers_group_name(course: Course) -> str:
    project_name = get_project_name(course)
    return f"{project_name}-reviewers"


def get_students_group_name(course: Course) -> str:
    project_name = get_project_name(course)
    return f"{project_name}-students"


def init_project_for_course(course: Course, skip_users: Optional[bool] = False):
    """
    Init gerrit project:
    1. Create reviewers group if not exists
    2. Synchronize reviewers group members with actual course teachers
    3. Create project: set gerrit reviewers group as owner, create master
    branch, grant necessary permissions to the gerrit reviewers group
    4. Create students group, grunt permissions to the project, for each
    enrolled student create gerrit group and add them to the students group
    5. Grant students access to the personal sandbox
    """
    # TODO: validate LDAP accounts before doing anything, update password hashes
    prefetch_related_objects([course], 'branches')
    # TODO: sync ldap accounts first
    gerrit_client = Gerrit(settings.GERRIT_API_URI,
                           auth=(settings.GERRIT_CLIENT_USERNAME,
                                 settings.GERRIT_CLIENT_HTTP_PASSWORD))
    # Init LDAP connection
    domain_component = settings.LDAP_DB_SUFFIX
    distinguished_name = f"cn={settings.LDAP_CLIENT_USERNAME},{domain_component}"
    ldap_connection = init_ldap_connection(uri=settings.LDAP_CLIENT_URI,
                                           dn=distinguished_name,
                                           password=settings.LDAP_CLIENT_PASSWORD)
    ldap_client = LDAPClient(ldap_connection, domain_component)
    # Create reviewers group
    reviewers_group_name = get_reviewers_group_name(course)  # self-owned group
    reviewers_group_res = gerrit_client.create_group(reviewers_group_name)
    if not reviewers_group_res.created:
        if not reviewers_group_res.already_exists:
            logger.error(f"Error on creating reviewers group. "
                         f"Response: {reviewers_group_res.text}")
            return
        reviewers_group_res = gerrit_client.get_group(reviewers_group_name)
    reviewers_group_uuid = reviewers_group_res.data["id"]
    # Create project
    project_name = get_project_name(course)
    project_description = f"Страница курса: {course.get_absolute_url()}"
    project_res = gerrit_client.create_project(project_name, {
        "description": project_description,
        "owners": [reviewers_group_uuid]
    })
    if not (project_res.created or project_res.already_exists):
        logger.error(f"Project hasn't been created. {project_res.text}")
        return
    gerrit_client.create_git_branch(project_name, "master")  # init master branch
    # Grant reviewers Push, Create Reference and Read Access to all branches
    res = grant_reviewers_access(gerrit_client, project_name, reviewers_group_uuid)
    if not res.ok:
        logger.error(f"Couldn't set permissions for group "
                     f"{reviewers_group_name}. {res.text}")
        return
    # Add course reviewers to the project
    reviewers = (CourseTeacher.objects
                 .filter(course=course,
                         roles=CourseTeacher.roles.reviewer)
                 .select_related("teacher"))
    for course_reviewer in reviewers:
        user = course_reviewer.teacher
        created = create_ldap_user(ldap_client, user)
        if not created:
            updated = update_ldap_user_password_hash(ldap_client, user)
            if not updated:
                logger.error(f"Password hash for user {user.pk} wasn't changed")
                return
    reviewers_group_members = [get_ldap_username(t.teacher) for t in reviewers]
    members_res = gerrit_client.get_group_members(reviewers_group_uuid)
    members = {m["username"] for m in members_res.data}
    to_delete = members.difference(reviewers_group_members)
    to_add = [m for m in reviewers_group_members if m not in members]
    response = gerrit_client.create_group_members(reviewers_group_uuid, to_add)
    if not response.ok:
        logger.error(f"Couldn't add new reviewers to group "
                     f"{reviewers_group_uuid}. Message: {response.text}")
        return
    res = gerrit_client.delete_group_members(reviewers_group_uuid, list(to_delete))
    if not res.ok:
        logger.warning(f"Couldn't remove reviewers from group "
                       f"{reviewers_group_uuid}. {res.text}")
    # Create students group that holds permissions common to all students
    students_group_name = get_students_group_name(course)
    students_group_res = gerrit_client.create_group(students_group_name, {
        # Only members of the owner group can administrate the owned group
        # (assign members, edit the group options)
        "owner_id": reviewers_group_uuid,
    })
    if not students_group_res.created:
        if not students_group_res.already_exists:
            logger.error(f"Student group `{students_group_name}` hasn't been created.")
            return
        students_group_res = gerrit_client.get_group(students_group_name)
    # Permits read master branch (allows to call git clone)
    students_group_uuid = students_group_res.data['id']
    res = grant_students_read_master(gerrit_client, project_name,
                                     students_group_uuid)
    if not res.ok:
        logger.error(f"Couldn't set permissions for group "
                     f"{students_group_name}. {res.text}")

    grant_personal_sandbox(gerrit_client, project_name, students_group_uuid)

    logger.info("Add test student to the project")
    add_student_to_project(gerrit_client=gerrit_client,
                           ldap_client=ldap_client,
                           student_profile=get_test_student_profile(course),
                           course=course,
                           students_group_uuid=students_group_uuid)

    if skip_users:
        return

    # For each enrolled student create separated branch
    enrollments = (Enrollment.active
                   .filter(course=course)
                   .select_related("student_profile__user",
                                   "student_profile__branch"))
    for e in enrollments:
        add_student_to_project(gerrit_client=gerrit_client,
                               ldap_client=ldap_client,
                               student_profile=e.student_profile,
                               course=course,
                               students_group_uuid=students_group_uuid)
    # TODO: What to do with notifications?
    ldap_connection.unbind_s()


def add_student_to_project(*, gerrit_client: Gerrit,
                           student_profile: StudentProfile,
                           course: Course,
                           students_group_uuid=None,
                           ldap_client: Optional[LDAPClient] = None):
    user = student_profile.user
    if students_group_uuid is None:
        students_group_name = get_students_group_name(course)
        students_group_res = gerrit_client.get_group(students_group_name)
        if not students_group_res.ok:
            logger.error('Students group for the project was not found')
            return
        students_group_uuid = students_group_res.data['id']
    # Create ldap user with create_ldap_user() method or update password hash
    created = create_ldap_user(ldap_client, user)
    if not created:
        logger.info(f"Updating password hash for user {user.pk}")
        updated = update_ldap_user_password_hash(ldap_client, user)
        if not updated:
            logger.error(f"Password hash for user {user.pk} wasn't changed")
            return
    project_name = get_project_name(course)
    # Make sure user group exists
    logger.info(f"Creating gerrit internal group for user {user.pk}")
    user_group_uuid = get_or_create_user_group(gerrit_client, user)
    if not user_group_uuid:
        return
    # Permits read master branch by adding to students group
    logger.info(f"Add user {user.pk} to the common student group")
    gerrit_client.include_group(students_group_uuid, user_group_uuid)
    # Create personal branch
    logger.info(f"Creating personal branch for user {user.pk}")
    git_branch_name = get_branch_name(student_profile, course)
    gerrit_client.create_git_branch(project_name, git_branch_name, {
        "revision": "master"
    })
    logger.info(f"Granting permissions to the user {user.pk}")
    # TODO: show errors
    grant_student_access(gerrit_client, project_name, git_branch_name,
                         user_group_uuid)


def get_test_student_profile(course: Course) -> StudentProfile:
    student = User(username='student', email='student')
    student.set_password(settings.GERRIT_TEST_STUDENT_PASSWORD)
    return StudentProfile(user=student, branch=course.main_branch)


def get_or_create_user_group(client: Gerrit, user: User):
    user_group = get_ldap_username(user)
    group_res = client.create_single_user_group(user_group)
    if not group_res.created:
        if not group_res.already_exists:
            # TODO: raise error?
            logger.error(f"Error on creating student group {user_group}. "
                         f"{group_res.text}. Skip")
            return
        logger.info(f"Gerrit internal group for user {user.pk} already exists")
        group_res = client.get_group(user_group)
    return group_res.data['id']


def add_users_to_project_by_email(course: Course, emails):
    client = Gerrit(settings.GERRIT_API_URI,
                    auth=(settings.GERRIT_CLIENT_USERNAME,
                          settings.GERRIT_CLIENT_HTTP_PASSWORD))
    # Check project exists
    project_name = get_project_name(course)
    project_res = client.get_project(project_name)
    if not project_res.ok:
        logger.error(f"Project {project_name} not found")
        return
    # Get project students group uuid
    students_group_name = get_students_group_name(course)
    students_group_res = client.get_group(students_group_name)
    if not students_group_res.ok:
        logger.error(f"Students project group {students_group_name} not found")
        return
    project_students_group_uuid = students_group_res.data['id']
    # Try to add each student from the email list to the project
    enrollments = (Enrollment.active
                   .filter(course_id=course.pk,
                           student__email__in=emails)
                   .select_related("student_profile__user",
                                   "student_profile__branch"))
    for e in enrollments:
        add_student_to_project(gerrit_client=client, student_profile=e.student,
                               course=course, students_group_uuid=project_students_group_uuid)


def get_gerrit_robot() -> User:
    return User.objects.get(username=settings.GERRIT_ROBOT_USERNAME)


def add_assignment_comment_about_new_change(student_assignment: StudentAssignment,
                                            change_url: str) -> AssignmentComment:
    course = student_assignment.assignment.course
    with translation.override(course.language):
        message = GerritRobotMessages.CHANGE_CREATED.format(link=change_url)
    comment = AssignmentComment(student_assignment=student_assignment,
                                type=AssignmentSubmissionTypes.COMMENT,
                                text=message, author=get_gerrit_robot())
    comment.save()
    return comment


def create_change(client, student_assignment: StudentAssignment) -> Optional[GerritChange]:
    """
    Create new change in Gerrit and store info in GerritChange model.
    """
    course = student_assignment.assignment.course
    enrollment = (Enrollment.objects
                  .filter(course=course, student=student_assignment.student)
                  .first())
    if not enrollment:
        logger.error("Failed to find enrollment")
    student_profile = enrollment.student_profile

    # Check that project exists
    project_name = get_project_name(course)
    project_res = client.get_project(project_name)
    if not project_res.ok:
        logger.error(f"Project {project_name} not found")
        return None

    # Check that student branch exists
    branch_name = get_branch_name(student_profile, course)
    branch_res = client.get_branch(project_name, branch_name)
    if not branch_res.ok:
        logger.error(f"Branch {branch_name} of {project_name} not found")
        return None

    change_subject = f'{student_assignment.assignment.title} ' \
                     f'({student_assignment.student.get_full_name()})'

    change_res = client.create_change(project_name, branch_name,
                                      subject=change_subject)
    if not change_res.created:
        return None
    change_id = change_res.json['id']
    logger.info(f'Created change {change_id}')
    site = student_assignment.assignment.course.main_branch.site
    change = GerritChange.objects.create(student_assignment=student_assignment,
                                         change_id=change_id, site=site)
    change_number = change_res.json['_number']
    gerrit_changes_uri = settings.GERRIT_API_URI.replace("/a/", "/c/")
    change_url = f'{gerrit_changes_uri}{project_name}/+/{change_number}'
    add_assignment_comment_about_new_change(student_assignment, change_url)
    return change


def get_or_create_change(client: Gerrit,
                         student_assignment: StudentAssignment) -> GerritChange:
    change = (GerritChange.objects
              .filter(student_assignment=student_assignment)
              .first())
    if not change:
        change = create_change(client, student_assignment)
        set_reviewers_for_change(client, change)
    return change


def set_reviewers_for_change(client: Gerrit, change: GerritChange):
    """Set reviewers and CC in Gerrit"""
    assignment = change.student_assignment.assignment
    student = change.student_assignment.student
    enrollment = student.get_enrollment(assignment.course_id)
    if not enrollment or not enrollment.student_group_id:
        return
    logger.info(f'Set reviewers for change {change.change_id}')
    assignees = StudentGroupService.get_assignees(enrollment.student_group,
                                                  assignment=assignment)
    for assignee in assignees:
        individual_group_uuid = get_or_create_user_group(client, assignee.teacher)
        client.set_reviewer(change.change_id, individual_group_uuid,
                            state='REVIEWER', notify='NONE')
    # The Change owner is admin (limitation of gerrit), not a student,
    # let's add them to CC to notify about updates
    individual_group_uuid = get_or_create_user_group(client, student)
    client.set_reviewer(change.change_id, individual_group_uuid, state='CC',
                        notify='NONE')


def list_change_files(client: Gerrit, change: GerritChange):
    response = client.list_files(change.change_id)
    if not response.ok:
        logger.info('Failed to retrieve change')
    data = response.json
    current_revision = data['current_revision']
    files = data['revisions'][current_revision]['files']
    return files
