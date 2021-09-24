import copy


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
