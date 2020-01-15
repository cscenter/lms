from rest_framework import permissions
"""Permissions implementation of learning.viewmixins"""


class CuratorAccessPermission(permissions.BasePermission):
    """Check user has curator permissions."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_curator

