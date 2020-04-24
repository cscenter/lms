import copy
import logging

from django.conf import settings
from django.db.models import prefetch_related_objects

from api.providers.gerrit import Gerrit
from core.models import Branch
from learning.models import Enrollment
from courses.models import Course, CourseTeacher
from users.models import User

logger = logging.getLogger(__name__)


def get_default_reviewers_project_access(group_uuid):
    return {
        "add": {
            "refs/*": {
                "permissions": {
                    "read": {
                        "exclusive": False,
                        "rules": {
                            group_uuid: {"action": "ALLOW", "force": False}
                        }
                    },
                    "push": {
                        "exclusive": True,
                        "rules": {
                            group_uuid: {"action": "ALLOW", "force": False}
                        }
                    },
                    "create": {
                        "exclusive": True,
                        "rules": {
                            group_uuid: {"action": "ALLOW", "force": False}
                        }
                    },
                }
            },
        },
    }


def get_default_students_project_access(group_uuid, git_branch_name):
    xallow = {
        "exclusive": False,
        "rules": {
            group_uuid: {
                "action": "ALLOW", "force": False
            }
        }
    }
    force_xallow = copy.deepcopy(xallow)
    force_xallow['rules'][group_uuid]['force'] = True
    return {
        # Remove all access rights on student branch not listed in `add` section
        "remove": {
            f"refs/heads/{git_branch_name}": {"permissions": {}},
            f"refs/for/refs/heads/{git_branch_name}": {"permissions": {}},
        },
        "add": {
            f"refs/heads/{git_branch_name}": {"permissions": {
                # A user must be able to clone or fetch the project in
                # order to create a new commit on their local system
                "read": xallow,
            }},
            f"refs/for/refs/heads/{git_branch_name}": {"permissions": {
                # Permits to upload a non-merge commit to
                # the refs/for/BRANCH, creating a new change for code review
                "push": xallow,
                # Irrespective of `addPatchSet` permission, change owners are
                # always allowed to upload new patch sets for their changes
            }}
        },
    }


def grant_reviewers_access(client, project_name, reviewers_group_uuid):
    """
    Grant reviewers Push, Create Reference and Read Access to `refs/*`
    """
    payload = get_default_reviewers_project_access(reviewers_group_uuid)
    # Workaround to avoid duplicates in old UI
    payload['remove'] = payload['add']
    return client.grant_permissions(project_name, payload)


def grant_student_access(client, project_name, git_branch_name, group_uuid):
    """Set permissions on branch for student group"""
    payload = get_default_students_project_access(group_uuid, git_branch_name)
    return client.grant_permissions(project_name, payload)


def grant_students_read_master(client, project_name, group_uuid):
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
    return client.grant_permissions(project_name, payload)


def grant_personal_sandbox(client, project_name, group_uuid):
    payload = {
        "remove": {
            "refs/heads/sandbox/${username}/*": {"permissions": {}},
        },
        "add": {
            # ${username} is always replaced with username of the currently
            # logged in user allowing to specify dynamic access control
            "refs/heads/sandbox/${username}/*": {
                "permissions": {
                    "create": {
                        "exclusive": True,
                        "rules": {
                            group_uuid: {"action": "ALLOW", "force": False}
                        }
                    },
                    # push force permission to be able to clean up stale
                    # branches
                    "push": {
                        "exclusive": True,
                        "rules": {
                            group_uuid: {"action": "ALLOW", "force": True}
                        }
                    },
                    "read": {
                        "exclusive": True,
                        "rules": {
                            group_uuid: {"action": "ALLOW", "force": False}
                        }
                    },
                }
            },
        },
    }
    return client.grant_permissions(project_name, payload)


def revoke_add_patch_set_permission(client, project_name):
    """
    By default, Add Patch Set is granted to Registered Users on refs/for/*,
    allowing all registered users to upload a new patch set to any change.
    Revoking this permission (by granting it to no groups and setting the
    "Exclusive" flag) will prevent users from uploading a patch set to a
    change they do not own.
    """
    payload = {
        "add": {
            "refs/for/*": {"permissions": {
                "addPatchSet": {
                    "exclusive": True,
                    "rules": {
                        "Registered Users": {"action": "BLOCK", "force": False}
                    }
                },
            }},
        },
    }
    # Workaround to remove duplicates on subsequent calls
    payload['remove'] = payload['add']
    return client.grant_permissions(project_name, payload)


def get_project_name(course):
    branch_code = course.main_branch.code
    course_name = course.meta_course.slug.replace("-", "_")
    if course.additional_branches.all():
        return f"{course_name}_{course.semester.year}"
    return f"{branch_code}/{course_name}_{course.semester.year}"


def get_reviewers_group_name(course):
    project_name = get_project_name(course)
    return f"{project_name}-reviewers"


def get_students_group_name(course):
    project_name = get_project_name(course)
    return f"{project_name}-students"


def init_project_for_course(course, skip_users=False):
    """
    Init gerrit project:
    1. Create reviewers group if not exists
    2. Synchronize reviewers group members with actual course teachers
    3. Create project: set gerrit reviewers group as owner, create master
    branch, grant neccessary permissions to the gerrit reviewers group
    4. Create students group, grunt permissions to the project, for each
    enrolled student create gerrit group and add them to the students group
    5. Grant students access to the personal sandbox
    """
    prefetch_related_objects([course], 'additional_branches')
    # TODO: sync ldap accounts first
    client = Gerrit(settings.GERRIT_API_URI,
                    auth=(settings.GERRIT_CLIENT_USERNAME,
                          settings.GERRIT_CLIENT_HTTP_PASSWORD))
    project_name = get_project_name(course)
    teachers = (CourseTeacher.objects
                .filter(course=course,
                        roles=CourseTeacher.roles.reviewer)
                .select_related("teacher"))
    # Creates separated self-owned group for project reviewers
    reviewers_group_name = get_reviewers_group_name(course)
    reviewers_group_members = [t.teacher.ldap_username for t in teachers]
    reviewers_group_res = client.create_group(reviewers_group_name, {
        "members": reviewers_group_members
    })
    # FIXME: Make sure all course teachers have LDAP account
    # Synchronize reviewers group members with course teachers
    if not reviewers_group_res.created:
        if not reviewers_group_res.already_exists:
            logger.error(f"Error on creating reviewers group for {project_name}"
                         f"Response message: {reviewers_group_res.text}")
            return
        reviewers_group_res = client.get_group(reviewers_group_name)
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
    project_description = f"Страница курса: {course.get_absolute_url()}"
    project_res = client.create_project(project_name, {
        "description": project_description,
        "owners": [reviewers_group_name]
    })
    if not (project_res.created or project_res.already_exists):
        logger.error(f"Project hasn't been created. {project_res.text}")
        return
    # Init master branch for the project
    client.create_git_branch(project_name, "master")
    # Grant reviewers Push, Create Reference and Read Access to all branches
    reviewers_group_uuid = reviewers_group_res.data["id"]
    res = grant_reviewers_access(client, project_name, reviewers_group_uuid)
    if not res.ok:
        logger.error(f"Couldn't set permissions for group "
                     f"{reviewers_group_name}. {res.text}")
        return
    # Create students group. Grant permissions common for all students
    # to this group
    students_group_name = get_students_group_name(course)
    students_group_res = client.create_group(students_group_name, {
        # Only members of the owner group can administrate the owned group
        # (assign members, edit the group options)
        "owner_id": reviewers_group_uuid,
    })
    if not students_group_res.created:
        if not students_group_res.already_exists:
            logger.error(f"Students group `{students_group_name}` hasn't "
                         f"been created.")
            return
        students_group_res = client.get_group(students_group_name)
    # Permits read master branch (allows to call git clone)
    project_students_group_uuid = students_group_res.data['id']
    res = grant_students_read_master(client, project_name,
                                     project_students_group_uuid)
    if not res.ok:
        logger.error(f"Couldn't set permissions for group "
                     f"{students_group_name}. {res.text}")

    grant_personal_sandbox(client, project_name, project_students_group_uuid)

    add_test_student_to_project(client, course, project_students_group_uuid)

    if skip_users:
        return

    # For each enrolled student create separated branch
    enrollments = (Enrollment.active
                   .filter(course_id=course.pk)
                   .select_related("student", "student__branch"))
    for e in enrollments:
        add_student_to_project(client, e.student, course,
                               project_students_group_uuid)
    # TODO: What to do with notifications?


def add_student_to_project(client: Gerrit, student: User, course: Course,
                           project_students_group_uuid=None):
    if project_students_group_uuid is None:
        students_group_name = get_students_group_name(course)
        students_group_res = client.get_group(students_group_name)
        if not students_group_res.ok:
            logger.error('Students group for the project not found')
            return
        project_students_group_uuid = students_group_res.data['id']
    project_name = get_project_name(course)
    # Make sure student group exists
    student_group_uuid = create_user_group(client, student)
    if not student_group_uuid:
        return
    # Permits read master branch by adding to students group
    client.include_group(project_students_group_uuid, student_group_uuid)
    # Create personal branch
    git_branch_name = student.get_abbreviated_name_in_latin()
    if course.additional_branches.all():
        git_branch_name = f"{student.branch.code}/{git_branch_name}"
    client.create_git_branch(project_name, git_branch_name, {
        "revision": "master"
    })
    # TODO: show errors
    grant_student_access(client, project_name, git_branch_name,
                         student_group_uuid)


def add_test_student_to_project(client: Gerrit, course: Course,
                                project_students_group_uuid):
    """
    Add user with uid=student for test purposes.

    Note:
        Make sure LDAP account for test student exist.
    """
    logger.debug("Add test student to the project")
    branch = Branch.objects.get_by_natural_key('spb', site_id=settings.SITE_ID)
    student = User(username='student', branch=branch)
    student.email = 'student'  # hack `.ldap_username`
    add_student_to_project(client, student, course,
                           project_students_group_uuid)


def create_user_group(client: Gerrit, user: User):
    user_group = user.ldap_username
    group_res = client.create_single_user_group(user_group)
    if not group_res.created:
        if not group_res.already_exists:
            # TODO: raise error?
            logger.error(f"Error on creating student group {user_group}. "
                         f"{group_res.text}. Skip")
            return
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
                   .select_related("student", "student__branch"))
    for e in enrollments:
        add_student_to_project(client, e.student, course,
                               project_students_group_uuid)
