from rules import always_true

from auth.permissions import perm_registry
from auth.registry import role_registry


def override_perm(perm):
    """
    Override permissions:
        * update global permissions rule set
        * update already registered roles which have ref to the old
        permission predicate
    """
    if perm not in perm_registry:
        return
    perm_registry.set_permission(perm)
    for _, role in role_registry.items():
        if role.permissions.rule_exists(perm.name):
            pred = always_true if perm.rule is None else perm.rule
            role.permissions.set_rule(perm.name, pred)
