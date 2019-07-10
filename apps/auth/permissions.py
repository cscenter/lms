from rules import RuleSet, always_true

all_permissions = RuleSet()


def add_perm(name, pred=None):
    if pred is None:
        pred = always_true
    all_permissions.add_rule(name, pred)
