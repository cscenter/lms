from rules import RuleSet


class RoleRuleSetRegistryError(Exception):
    pass


class AlreadyRegistered(RoleRuleSetRegistryError):
    pass


class PermissionAlreadyRegistered(RoleRuleSetRegistryError):
    """
    Throw this exception when two rules with the same name are binded
    to different predicate functions.
    """
    pass


class NotRegistered(RoleRuleSetRegistryError):
    pass


class RoleRuleSetRegistry:
    """
    This registry helps to organize Role-based access control. Inheritance
    between roles is not supported.

    Each record in the registry is a role (R) associated with
    `rules.RuleSet` instance (P).
    """
    def __init__(self):
        self._registry = {}

    def register(self, role_name, rule_set: RuleSet):
        """
        Registers the given rule set for given role name.
        If notification already registered, this will raise AlreadyRegistered.
        """

        if role_name in self._registry:
            msg = 'The role name {} is already registered.'.format(role_name)
            raise AlreadyRegistered(msg)
        # If rule with the same name is already registered in another rule set,
        # make sure they are both binded to the same predicate function
        for rule_name in rule_set:
            for another_role_name, another_rule_set in self._registry.items():
                for another_rule_name in another_rule_set:
                    if rule_name == another_rule_name:
                        another_predicate = another_rule_set[another_rule_name]
                        if another_predicate != rule_set[rule_name]:
                            msg = ('The permission name {} registered at least '
                                   'in two roles `{}` and `{}` but binded to '
                                   'different predicates'.format(rule_name,
                                                                 role_name,
                                                                 another_role_name))
                            raise PermissionAlreadyRegistered(msg)
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


role_registry = RoleRuleSetRegistry()
