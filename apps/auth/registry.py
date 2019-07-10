from typing import Iterable

from rules import RuleSet

from auth.permissions import all_permissions


class RolePermissionsRegistryError(Exception):
    pass


class AlreadyRegistered(RolePermissionsRegistryError):
    pass


class PermissionNotRegistered(RolePermissionsRegistryError):
    pass


class NotRegistered(RolePermissionsRegistryError):
    pass


class RolePermissionsRegistry:
    """
    This registry helps to organize Role-based access control. Inheritance
    between roles is not supported.

    Each record in the registry is a role (R) associated with
    `rules.RuleSet` instance (P).
    """
    def __init__(self):
        self._registry = {}

    def register(self, role_name, permissions: Iterable[str]):
        """
        Registers the given rule set for given role name.
        If notification already registered, this will raise AlreadyRegistered.
        """

        if role_name in self._registry:
            msg = 'The role name {} is already registered.'.format(role_name)
            raise AlreadyRegistered(msg)
        rule_set = RuleSet()
        for permission in permissions:
            if permission not in all_permissions:
                msg = ("Permission `{}` is not registered in global rule set. "
                       "Call `auth.permissions.add_perm` "
                       "first.".format(permission))
                raise PermissionNotRegistered(msg)
            rule_set.add_rule(permission, all_permissions[permission])
        self._registry[role_name] = rule_set

    def unregister(self, role_name):
        """
        Unregisters the given role.

        If a role isn't already registered, this will raise NotRegistered.
        """
        if role_name not in self._registry:
            raise NotRegistered('The role name %s is not '
                                'registered' % role_name)
        del self._registry[role_name]

    def __contains__(self, role_name):
        return role_name in self._registry

    def __len__(self):
        return len(self._registry)

    def __iter__(self):
        return self._registry

    def __getitem__(self, role_name):
        return self._registry[role_name]

    def items(self):
        return self._registry.items()


role_registry = RolePermissionsRegistry()
