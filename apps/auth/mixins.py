from django.contrib.auth.mixins import PermissionRequiredMixin as _PermissionRequiredMixin


# FIXME: check that perms registered in all_permissions?
class PermissionRequiredMixin(_PermissionRequiredMixin):
    """
    CBV mixin to provide object-level permission checking to views. Best used
    with views that inherit from ``SingleObjectMixin`` (``DetailView``,
    ``UpdateView``, etc.), though not required.

    The single requirement is for a ``get_object`` method to be available
    in the view. If there's no ``get_object`` method, permission checking
    is model-level, that is exactly like Django's ``PermissionRequiredMixin``.
    """
    def get_permission_object(self):
        """
        Override this method to provide the object to check for permission
        against. Returns None by default, it allows to check regular permissions
        """
        return None

    def has_permission(self):
        obj = self.get_permission_object()
        perms = self.get_permission_required()
        return self.request.user.has_perms(perms, obj)
