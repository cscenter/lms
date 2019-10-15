from rules import predicate

from auth.permissions import perm_registry
from auth.registry import role_registry


def override_perm(name, pred=None):
    """
    Override permissions:
        * update global permissions rule set
        * update already registered roles which have ref to the old
        permission predicate
    """
    if name not in perm_registry:
        return
    if pred is None:
        pred = predicate(lambda: True, name=name)
    perm_registry.set_permission(name, pred)
    for role in role_registry.values():
        if role.permissions.rule_exists(name):
            role.permissions.set_rule(name, pred)
