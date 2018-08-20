import json
import logging
from urllib.parse import urljoin, quote_plus

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

GERRIT_MAGIC_JSON_PREFIX = b")]}\'\n"

REQUIRED_SETTINGS = [
    "GERRIT_API_URI",
    "GERRIT_CLIENT_USERNAME",
    "GERRIT_CLIENT_PASSWORD",
]

for attr in REQUIRED_SETTINGS:
    if not hasattr(settings, attr):
        raise ImproperlyConfigured(
            "Please add {0!r} to your settings module".format(attr))


class GerritResponse:
    def __init__(self, response):
        self._response = response
        logger.debug(f"Response raw content: {response.text}")

    @property
    def json(self):
        # FIXME: Invalid json content: b'Account Not Found: sheina.ekaterina.s@yandex.ru\n'
        """
        Encode response content as json.

        To prevent against Cross Site Script Inclusion (XSSI) attacks,
        the JSON response body starts with a magic prefix line,
        we should remove it before encoding.
        """
        content = self._response.content
        if content.startswith(GERRIT_MAGIC_JSON_PREFIX):
            content = content[len(GERRIT_MAGIC_JSON_PREFIX):]
        try:
            return json.loads(content)
        except ValueError:
            logging.error('Invalid json content: %s', content)
            raise

    @property
    def data(self):
        return self.json

    @property
    def ok(self):
        return self._response.ok

    @property
    def created(self):
        if self._response.request.method not in ["PUT", "POST"]:
            raise AttributeError(f"Method is not supported "
                                 f"for {self._response.request.method}")
        return self._response.status_code == 201

    @property
    def already_exists(self):
        if self._response.request.method not in ["PUT", "POST"]:
            raise AttributeError(f"Method is not supported "
                                 f"for {self._response.request.method}")
        return (self._response.status_code in [412, 409] and
                "already exists" in self._response.text)

    @property
    def text(self):
        return self._response.text


class Gerrit:
    def __init__(self, api_url, auth):
        self.api_url = api_url
        self.auth = auth

    def _request(self, method, uri, **kwargs):
        url = urljoin(self.api_url, uri)
        headers = kwargs.pop("headers", {})
        headers["Accept"] = "application/json"
        if method == "PUT":
            # Create a new resource but not overwrite an existing
            # The server will respond with HTTP 412 (Precondition Failed)
            # if the named resourse is already exists.
            headers["If-None-Match"] = "*"
        kwargs["headers"] = headers
        response = requests.request(method, url, auth=self.auth, **kwargs)
        return GerritResponse(response)

    def get_group(self, group_name):
        return self._request("GET", f"groups/{quote_plus(group_name)}")

    def create_group(self, group_name, payload=None):
        group_uri = f"groups/{quote_plus(group_name)}"
        payload = payload or {}
        return self._request("PUT", group_uri, json={
            **payload,
            "name": group_name
        })

    def create_single_user_group(self, group_name, payload=None):
        payload = payload or {}
        return self.create_group(group_name, {
            "name": group_name,
            "members": [group_name],
            **payload
        })

    def include_group(self, parent_group_id, groups):
        """
        Adds one or several groups as subgroups to a Gerrit internal group.

        group_id
            Identifier for a group. This can be:
            * the UUID of the group
            * the legacy numeric ID of the group
            * the name of the group if it is unique
        """
        if not isinstance(groups, list):
            groups = [groups]
        uri = f"groups/{quote_plus(parent_group_id)}/groups"
        return self._request("POST", uri, json={"groups": groups})

    def get_group_members(self, group_id):
        return self._request("GET", f"groups/{quote_plus(group_id)}/members/")

    def create_group_members(self, group_id, members: list):
        logger.debug(f"Add members {members} to group {group_id}")
        uri = f"groups/{quote_plus(group_id)}/members.add"
        return self._request("POST", uri, json={
            "members": members
        })

    def delete_group_members(self, group_id, members: list):
        logger.debug(f"Delete members {members} from group {group_id}")
        uri = f"groups/{quote_plus(group_id)}/members.delete"
        return self._request("POST", uri, json={
            "members": members
        })

    def create_branch(self, project, branch_name, payload=None):
        logger.debug(f"Create branch [{branch_name}] for project {project}")
        branch_uri = "projects/{}/branches/{}".format(
            quote_plus(project),
            quote_plus(branch_name)
        )
        payload = payload or {}
        return self._request("PUT", branch_uri, json={
            **payload
        })

    def create_permissions(self, project, permissions: dict):
        """
        On success returns information about all access rights for a project.
        """
        project_access_uri = f"projects/{quote_plus(project)}/access"
        return self._request("POST", project_access_uri, json=permissions)

    def create_student_permissions(self, project, branch, group_uuid):
        """Set permissions on branch for student group"""
        xallow = {
            "exclusive": False,
            "rules": {
                group_uuid: {
                    "action": "ALLOW", "force": False
                }
            }
        }
        payload = {
            "add": {
                f"refs/heads/{branch}": {"permissions": {
                    "read": xallow,
                }},
                f"refs/for/refs/heads/{branch}": {"permissions": {
                    # Permits to upload a non-merge commit to
                    # the refs/for/BRANCH
                    "push": xallow,
                    "addPatchSet": xallow,
                }}
            },
        }
        return self.create_permissions(project, payload)

    def get_project(self, project_name):
        # https://gerrit-review.googlesource.com/Documentation/rest-api-projects.html#project-info
        project_uri = f"projects/{quote_plus(project_name)}"
        return self._request("GET", project_uri)

    def create_project(self, project_name, payload=None):
        project_uri = f"projects/{quote_plus(project_name)}"
        payload = payload or {}
        return self._request("PUT", project_uri, json={
            "submit_type": "INHERIT",
            "create_empty_commit": "TRUE",
            "use_contributor_agreements": "FALSE",
            "use_signed_off_by": "FALSE",
            "reject_empty_commit": "TRUE",
            # Project parent is `All-Projects` by default
            **payload
        })



