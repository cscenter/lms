from auth.permissions import Role

from .errors import AlreadyRegistered, NotRegistered


class RolePermissionsRegistry:
    """
    This registry helps to organize Role-based access control. Has a
    predefined 'default' role to check object permissions for anonymous users.

    Each record in the registry is a role (R) associated with an
    `rules.RuleSet` instance (P). Role inheritance is not supported.
    """

    _ANONYMOUS_ROLE = '_anon'
    _AUTHENTICATED_ROLE = '_auth'

    def __init__(self):
        self._registry = {}
        self._register_default_roles()

    def _register_default_roles(self):
        self.register(Role(id=self._ANONYMOUS_ROLE, description='Anonymous Role',
                           priority=1000, permissions=[]))
        self.register(Role(id=self._AUTHENTICATED_ROLE, description='Authenticated Role',
                           priority=900, permissions=[]))

    def register(self, role: Role):
        """
        Registers the given rule set for given role name.
        If notification already registered, this will raise AlreadyRegistered.
        """

        if role.code in self._registry:
            raise AlreadyRegistered(f"Cannot register `{role}`. Role "
                                    f"{self._registry[role.code]} is already "
                                    f"registered with the same code")
        self._registry[role.code] = role

    def unregister(self, role: Role):
        """
        Unregisters the given role.

        If a role isn't already registered, this will raise NotRegistered.
        """
        if role.code not in self._registry:
            raise NotRegistered('The role %s is not '
                                'registered' % role.code)
        del self._registry[role.code]

    def __contains__(self, role):
        if isinstance(role, Role):
            return role.code in self._registry
        else:
            return role in self._registry

    def __len__(self):
        return len(self._registry)

    def __iter__(self):
        return self._registry

    def __getitem__(self, role) -> Role:
        if isinstance(role, Role):
            return self._registry[role.code]
        else:
            return self._registry[role]

    @property
    def anonymous_role(self) -> Role:
        return self._registry[self._ANONYMOUS_ROLE]

    @property
    def authenticated_role(self) -> Role:
        return self._registry[self._AUTHENTICATED_ROLE]

    def items(self):
        return self._registry.items()


role_registry = RolePermissionsRegistry()
