import pytest
import rules

from auth.backends import RBACModelBackend
from auth.registry import role_registry, AlreadyRegistered, \
    PermissionAlreadyRegistered
from users.tests.factories import UserFactory


def test_registry():
    rule_set1 = rules.RuleSet()
    predicate1 = rules.is_group_member('special1')
    rule_set1.add_rule('is_predicate', predicate1)
    rule_set2 = rules.RuleSet()
    predicate2 = rules.is_group_member('special2')
    rule_set2.add_rule('is_predicate', predicate2)
    role_registry.register('role1', rule_set1)
    with pytest.raises(AlreadyRegistered):
        role_registry.register('role1', rule_set2)
    with pytest.raises(PermissionAlreadyRegistered):
        role_registry.register('role2', rule_set2)
    rule_set2.clear()
    rule_set2.add_rule('is_predicate', predicate1)
    role_registry.register('role2', rule_set2)


@pytest.mark.django_db
def test_backend():
    backend = RBACModelBackend()
    user = UserFactory()
    assert not backend.has_perm(user, 'permission_name')
    rule_set = rules.RuleSet()
    rule_set.add_rule('is_active', rules.is_active)
    role_registry.register('role', rule_set)
    assert not user.has_perm('is_active')
    user.roles = ['role']
    assert user.has_perm('is_active')
