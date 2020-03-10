from auth.permissions import Role
from .errors import AlreadyRegistered, NotRegistered


# TODO: в теории можно связывать роли, а не только permissions. Подумать о наследовании ролей по аналогии с add_relation
class RolePermissionsRegistry:
    """
    This registry helps to organize Role-based access control. Inheritance
    between roles is not supported.

    Each record in the registry is a role (R) associated with
    `rules.RuleSet` instance (P).
    """

    DEFAULT_ROLE_CODE = '_default'

    def __init__(self):
        self._registry = {}
        self._register_default_role()

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
            raise NotRegistered('The role name %s is not '
                                'registered' % role.code)
        del self._registry[role.code]

    def _register_default_role(self):
        self.register(Role(code=self.DEFAULT_ROLE_CODE,
                           name='Default Role',
                           permissions=[]))

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
    def default_role(self) -> Role:
        return self._registry[self.DEFAULT_ROLE_CODE]

    def items(self):
        return self._registry.items()


role_registry = RolePermissionsRegistry()
