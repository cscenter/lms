from rest_framework import permissions
"""Permissions implementation of learning.viewmixins"""


class CuratorAccessPermission(permissions.BasePermission):
    """Check user has curator permissions."""

    def has_permission(self, request, view):
        return request.user.is_authenticated() and request.user.is_curator


class StudentAccessPermission(permissions.BasePermission):
    """
    Check user has active student or volunteer group.
    Active means user is not expelled.
    """

    def has_permission(self, request, view):
        is_active_student = (request.user.is_student and
                             not request.user.is_expelled)
        return is_active_student or request.user.is_curator
