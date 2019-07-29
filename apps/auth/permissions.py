from rules import RuleSet, predicate

all_permissions = RuleSet()


def add_perm(name, pred=None):
    if pred is None:
        pred = predicate(lambda: True, name=name)
    all_permissions.add_rule(name, pred)
