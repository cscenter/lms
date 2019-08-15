from rules import predicate

from auth.permissions import all_permissions
from auth.registry import role_registry


def override_perm(name, pred=None):
    """
    Override permissions:
        * update global permissions rule set
        * update already registered roles which have ref to the old
        permission predicate
    """
    if not all_permissions.rule_exists(name):
        return
    if pred is None:
        pred = predicate(lambda: True, name=name)
    all_permissions.set_rule(name, pred)
    for _, role_perms in role_registry.items():
        if role_perms.rule_exists(name):
            role_perms.set_rule(name, pred)