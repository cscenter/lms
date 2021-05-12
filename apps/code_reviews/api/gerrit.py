import base64
import json
import logging
from enum import IntEnum
from urllib.parse import quote_plus, urljoin

import requests

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# TODO: refactoring based on this article https://medium.com/@hakibenita/working-with-apis-the-pythonic-way-484784ed1ce0 (see exceptions part)

logger = logging.getLogger(__name__)

REQUIRED_SETTINGS = [
    "GERRIT_API_URI",
    "GERRIT_CLIENT_USERNAME",
    "GERRIT_CLIENT_HTTP_PASSWORD",
]

for attr in REQUIRED_SETTINGS:
    if not hasattr(settings, attr):
        raise ImproperlyConfigured(
            "Please add {0!r} to your settings module".format(attr))


class ResponseStatus(IntEnum):
    """
    Gerrit response codes: https://review.compscicenter.ru/Documentation/rest-api.html#response-codes
    """
    SUCCESS = 200
    CREATED = 201
    NO_CONTENT = 204  # Empty response
    BAD_REQUEST = 400  # Bad Request
    NO_ACCESS = 403  # You don't have enough permissions
    NOT_FOUND = 404  # Resource (project, branch, change) not found
    NOT_ALLOWED = 405  # Method Not Allowed
    CONFLICT = 409  # Current state of the resource does not allow this operation
    ALREADY_EXISTS = 412  # Precondition failed, resource already exists


class Response:
    """
    Wrapper for `requests.models.Response`.

    To prevent against Cross Site Script Inclusion (XSSI) attacks,
    the JSON response body in gerrit starts with a magic prefix line,
    remove it before encoding body to json.
    """

    MAGIC_JSON_PREFIX = b")]}\'\n"

    def __init__(self, response):
        self._response = response
        logger.debug(f"Response raw content: {response.text}")

    @property
    def json(self):
        # FIXME: Invalid json content: b'Account Not Found: sheina.ekaterina.s@yandex.ru\n'
        """
        Encode response content as json.
        """
        content = self._response.content
        if content.startswith(self.MAGIC_JSON_PREFIX):
            content = content[len(self.MAGIC_JSON_PREFIX):]
        try:
            return json.loads(content)
        except ValueError:
            logging.error('Invalid json content: %s', content)
            raise

    @property
    def text(self):
        return self._response.text

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
        return self._response.status_code == ResponseStatus.CREATED

    @property
    def no_content(self):
        return self._response.status_code == ResponseStatus.NO_CONTENT

    @property
    def already_exists(self):
        if self._response.request.method not in ["PUT", "POST"]:
            raise AttributeError(f"Method is not supported "
                                 f"for {self._response.request.method}")
        return (self._response.status_code in [ResponseStatus.ALREADY_EXISTS, ResponseStatus.CONFLICT] and
                "already exists" in self._response.text)


# TODO: create service user (e.g. for Jenkins)
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
            # if the named resource already exists.
            headers["If-None-Match"] = "*"
        kwargs["headers"] = headers
        response = requests.request(method, url, auth=self.auth, **kwargs)
        return Response(response)

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

        `parent_group_id` is identifier for a group. This can be:
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

    def create_group_member(self, group_id, account_id):
        logger.debug(f"Add member {account_id} to the group {group_id}")
        uri = f"groups/{quote_plus(group_id)}/members/{quote_plus(account_id)}"
        return self._request("PUT", uri)

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

    def create_git_branch(self, project_name, branch_name, payload=None):
        logger.debug(f"Create branch [{branch_name}] for {project_name}")
        branch_uri = "projects/{}/branches/{}".format(
            quote_plus(project_name),
            quote_plus(branch_name)
        )
        payload = payload or {}
        return self._request("PUT", branch_uri, json={**payload})

    def get_permissions(self, project_name):
        """
        Returns information about all access rights for a project.
        """
        project_access_uri = f"projects/{quote_plus(project_name)}/access"
        return self._request("GET", project_access_uri)

    def grant_permissions(self, project_name, permissions: dict):
        """
        On success returns information about all access rights for a project.
        """
        project_access_uri = f"projects/{quote_plus(project_name)}/access"
        return self._request("POST", project_access_uri, json=permissions)

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

    def get_branch(self, project_name, branch_name):
        branch_uri = f"projects/{quote_plus(project_name)}/branches/{quote_plus(branch_name)}"
        return self._request("GET", branch_uri)

    def get_account(self, account_id):
        account_uri = f"accounts/{quote_plus(account_id)}"
        return self._request("GET", account_uri)

    def get_account_external_ids(self, account_id):
        # TODO: needs Access Database capability?
        account_uri = f"accounts/{quote_plus(account_id)}/external.ids"
        return self._request("GET", account_uri)

    def set_account_name(self, account_id, new_name):
        account_uri = f"accounts/{quote_plus(account_id)}/name"
        return self._request("PUT", account_uri, json={
            "name": new_name
        })

    def set_reviewer(self, change_id, reviewer, **payload):
        change_reviewers_uri = f'changes/{change_id}/reviewers'
        return self._request('POST', change_reviewers_uri, json={
            'reviewer': reviewer,
            **payload
        })

    def create_change(self, project_name, branch_name, subject, **payload):
        changes_uri = 'changes/'
        return self._request('POST', changes_uri, json={
            'project': project_name,
            'subject': subject,
            'branch': branch_name,
            **payload
        })

    def get_change(self, change_id):
        changes_uri = f'changes/{change_id}'
        return self._request('GET', changes_uri)

    def list_files(self, change_id):
        changes_uri = f'changes/{change_id}?o=CURRENT_REVISION&o=CURRENT_FILES'
        return self._request('GET', changes_uri)

    def delete_file(self, change_id, path_to_file):
        change_edit_uri = f'changes/{change_id}/edit/{path_to_file}'
        return self._request('DELETE', change_edit_uri)

    def upload_file(self, change_id, path_to_file, file):
        change_edit_uri = f'changes/{change_id}/edit/{path_to_file}'

        content = file.read()
        binary_content = f'data:text/plain;base64,{base64.b64encode(content).decode()}'
        return self._request('PUT', change_edit_uri, json={
            'binary_content': binary_content
        })

    def get_change_edit(self, change_id):
        change_edit_uri = f'changes/{change_id}/edit'
        return self._request('GET', change_edit_uri)

    def publish_change_edit(self, change_id):
        change_edit_uri = f'changes/{change_id}/edit:publish'
        return self._request('POST', change_edit_uri)

    def delete_change_edit(self, change_id):
        change_edit_uri = f'changes/{change_id}/edit'
        return self._request('DELETE', change_edit_uri)
