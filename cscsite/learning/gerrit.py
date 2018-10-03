import logging
import textwrap

from django.conf import settings

from api.providers.gerrit import Gerrit
from learning.models import CourseOfferingTeacher, Enrollment
from users.models import CSCUser

logger = logging.getLogger(__name__)


def grant_reviewers_access(client, project_name, reviewers_group_uuid):
    """Grant reviewers Push, Create Reference and Read Access to all branches"""
    xallow = {
        "exclusive": True,
        "rules": {reviewers_group_uuid: {"action": "ALLOW", "force": False}}
    }
    read_xallow = xallow.copy()
    read_xallow["exclusive"] = False
    payload = {
        "add": {
            "refs/*": {"permissions": {
                "read": read_xallow,
                "push": xallow,
                "create": xallow
            }},
        },
    }
    return client.create_permissions(project_name, payload)


def permits_students_read_master(client, project_name, group_uuid):
    xallow = {
        "exclusive": False,
        "rules": {group_uuid: {"action": "ALLOW", "force": False}}
    }
    payload = {
        "add": {
            "refs/heads/master": {"permissions": {
                "read": xallow,
            }},
        },
    }
    return client.create_permissions(project_name, payload)


def get_project_name(course_offering):
    city_code = course_offering.get_city()
    course_name = course_offering.course.slug.replace("-", "_")
    if course_offering.is_correspondence:
        return f"{course_name}_{course_offering.semester.year}"
    return f"{city_code}/{course_name}_{course_offering.semester.year}"


def init_project_for_course(course_offering, skip_users=False):
    client = Gerrit(settings.GERRIT_API_URI,
                    auth=(settings.GERRIT_CLIENT_USERNAME,
                          settings.GERRIT_CLIENT_PASSWORD))
    project_name = get_project_name(course_offering)
    teachers = (CourseOfferingTeacher.objects
                .filter(course_offering=course_offering,
                        roles=CourseOfferingTeacher.roles.reviewer)
                .select_related("teacher"))
    # Creates separated self-owned group for project reviewers
    reviewers_group = f"{project_name}-reviewers"
    reviewers_group_members = [t.teacher.ldap_username for t in teachers]
    reviewers_group_res = client.create_group(reviewers_group, {
        "members": reviewers_group_members
    })
    # FIXME: Make sure all course teachers have LDAP account
    if not reviewers_group_res.created:
        if not reviewers_group_res.already_exists:
            logger.error(f"Error creating reviewers group for {project_name}. "
                         f"Response message: {reviewers_group_res.text}")
            return
        # Update reviewers group members
        reviewers_group_res = client.get_group(reviewers_group)
        reviewers_group_uuid = reviewers_group_res.data["id"]
        members_res = client.get_group_members(reviewers_group_uuid)
        members = {m["username"] for m in members_res.data}
        to_delete = members.difference(reviewers_group_members)
        to_add = [m for m in reviewers_group_members if m not in members]
        res = client.create_group_members(reviewers_group_uuid, to_add)
        if not res.ok:
            logger.error(f"Couldn't add new reviewers to group "
                         f"{reviewers_group_uuid}. Message: {res.text}")
            return
        res = client.delete_group_members(reviewers_group_uuid, list(to_delete))
        if not res.ok:
            logger.warning(f"Couldn't remove reviewers from group "
                           f"{reviewers_group_uuid}. {res.text}")
    project_description = textwrap.dedent(f"""\
            Страница курса: \
            https://compscicenter.ru{course_offering.get_absolute_url()}
        """).strip()
    # FIXME: how to set `Create a new change for every commit not in the target branch` to False? Mb for all projects
    project_res = client.create_project(project_name, {
        "description": project_description,
        "owners": [reviewers_group]
    })
    if not (project_res.created or project_res.already_exists):
        logger.error(f"Project hasn't been created. {project_res.text}")
        return
    # Init master branch for the project
    client.create_branch(project_name, "master")
    # Grant reviewers Push, Create Reference and Read Access to all branches
    reviewers_group_uuid = reviewers_group_res.data["id"]
    # FIXME: права добавляются N-раз
    res = grant_reviewers_access(client, project_name, reviewers_group_uuid)
    if not res.ok:
        logger.error(f"Couldn't set permissions for group "
                     f"{reviewers_group}. {res.text}")
        return
    # Create students group. Grant permissions common for all students
    # to this group
    students_group = f"{project_name}-students"
    students_group_res = client.create_group(students_group, {
        # Only members of the owner group can administrate the owned group
        # (assign members, edit the group options)
        "owner_id": reviewers_group_uuid,
    })
    if not students_group_res.created:
        if not students_group_res.already_exists:
            logger.error(f"Students group `{students_group}` hasn't "
                         f"been created.")
            return
        students_group_res = client.get_group(students_group)
    # Common access rules for reading master branch
    project_students_group_uuid = students_group_res.data['id']
    res = permits_students_read_master(client, project_name,
                                       project_students_group_uuid)
    if not res.ok:
        logger.error(f"Couldn't set permissions for group "
                     f"{students_group}. {res.text}")

    if skip_users:
        return

    # For each enrolled student create separated branch
    enrollments = (Enrollment.active
                   .filter(course_offering_id=course_offering.pk)
                   .select_related("student"))
    for e in enrollments:
        add_student_to_project(client, e.student, project_name,
                               project_students_group_uuid, course_offering)
    # TODO: What to do with notifications?


def add_student_to_project(client: Gerrit, student: CSCUser, project_name,
                           project_students_group_uuid, course_offering):
    # Make sure student group exists
    student_group_uuid = create_user_group(client, student)
    if not student_group_uuid:
        return
    # Permits students read master branch
    client.include_group(project_students_group_uuid, student_group_uuid)
    branch_name = student.get_abbreviated_name_in_latin()
    if course_offering.is_correspondence:
        assert student.city_id is not None
        branch_name = f"{student.city_id}/{branch_name}"
    # FIXME: What if already exists?
    client.create_branch(project_name, branch_name, {
        "revision": "master"
    })
    # TODO: show errors
    # FIXME: Duplicates on repeated call
    client.create_student_permissions(project_name, branch_name,
                                      student_group_uuid)


def create_user_group(client: Gerrit, user: CSCUser):
    user_group = user.ldap_username
    group_res = client.create_single_user_group(user_group)
    if not group_res.created:
        if not group_res.already_exists:
            # TODO: raise error?
            logger.error(f"Error creating student group {user_group}. "
                         f"{group_res.text}. Skip")
            return
        group_res = client.get_group(user_group)
    return group_res.data['id']


def add_users_to_project_by_email(course_offering, emails):
    client = Gerrit(settings.GERRIT_API_URI,
                    auth=(settings.GERRIT_CLIENT_USERNAME,
                          settings.GERRIT_CLIENT_PASSWORD))
    # Check project exists
    project_name = get_project_name(course_offering)
    project_res = client.get_project(project_name)
    if not project_res.ok:
        logger.error(f"Project {project_name} not found")
        return
    # Get project students group uuid
    students_group = f"{project_name}-students"
    students_group_res = client.get_group(students_group)
    if not students_group_res.ok:
        logger.error(f"Students project group {students_group} not found")
        return
    project_students_group_uuid = students_group_res.data['id']
    # Try to add each student from the email list to the project
    enrollments = (Enrollment.active
                   .filter(course_offering_id=course_offering.pk,
                           student__email__in=emails)
                   .select_related("student"))
    for e in enrollments:
        print(e.student)
        add_student_to_project(client, e.student, project_name,
                               project_students_group_uuid, course_offering)
