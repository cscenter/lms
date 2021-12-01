from typing import TYPE_CHECKING, Any, List, Optional, Type

from rest_framework import exceptions

from django.contrib.auth.mixins import \
    PermissionRequiredMixin as _PermissionRequiredMixin
from django.contrib.auth.models import _user_has_perm

from auth.permissions import Permission
from core.http import HttpRequest

if TYPE_CHECKING:
    from rest_framework.views import APIView
    RolePermissionRequiredMixinBase = APIView
else:
    RolePermissionRequiredMixinBase = object

# FIXME: statically check that perms registered in all_permissions?


class PermissionRequiredMixin(_PermissionRequiredMixin):
    """
    CBV mixin to provide object- or model-level permissions checking to views.

    Best used with views that inherit from ``SingleObjectMixin``
    (``DetailView``, ``UpdateView``, etc.), though not required.
    """
    request: HttpRequest

    def get_permission_object(self) -> Optional[Any]:
        """
        Override this method to provide an object to check for permissions.
        Returning None allows to check for model permissions.
        """
        return None

    def has_permission(self):
        obj = self.get_permission_object()
        perms = self.get_permission_required()
        # FIXME: no need to check all permissions (see `has_perms` implementation)
        return self.request.user.has_perms(perms, obj)


class RolePermissionRequiredMixin(RolePermissionRequiredMixinBase):
    """
    This mixin overrides Django Rest Framework `.check_permissions()`
    and allows to check access for a given permission object in a
    `.dispatch()` method while DRF checks only model-level permissions
    """
    # TODO: add check: make sure all Permission's are registered in a perm_registry and issubclass of Permission
    permission_classes: List[Type[Permission]]

    def get_permission_object(self) -> Optional[Any]:
        """
        Override this method to provide an object to check for permissions.
        Returning `None` allows to check for model permission on
        `auth.backends.RBACPermission` backend.
        """
        return None

    def check_permissions(self, request) -> None:
        permission_object = self.get_permission_object()
        for permission_class in self.permission_classes:
            permission = permission_class()
            if not permission.has_object_permission(request, self, obj=permission_object):
                if request.authenticators and not request.successful_authenticator:
                    raise exceptions.NotAuthenticated()
                raise exceptions.PermissionDenied()
