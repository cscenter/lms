import pytest
import rules

from auth.backends import RBACModelBackend
from auth.permissions import add_perm
from auth.registry import role_registry, AlreadyRegistered, \
    PermissionNotRegistered, RolePermissionsRegistry
from users.tests.factories import UserFactory


def test_registry(mocker):
    mocker.patch.dict(role_registry._registry, clear=True)
    predicate1 = rules.is_group_member('special1')
    add_perm('is_predicate', predicate1)
    with pytest.raises(PermissionNotRegistered):
        role_registry.register('role1', ['void'])
    role_registry.register('role1', ['is_predicate'])
    assert 'role1' in role_registry
    with pytest.raises(AlreadyRegistered):
        role_registry.register('role1', ['is_predicate'])


@pytest.mark.django_db
def test_backend(mocker):
    mocker.patch.dict(role_registry._registry, clear=True)
    backend = RBACModelBackend()
    user = UserFactory()
    assert not backend.has_perm(user, 'permission_name')
    add_perm('is_active', rules.is_active)
    role_registry.register('role', ['is_active'])
    assert not user.has_perm('is_active')
    user.roles = ['role']
    assert user.has_perm('is_active')


@pytest.mark.django_db
def test_backend_has_perm(mocker):
    mocker.patch.dict(role_registry._registry, clear=True)
    user = UserFactory()
    add_perm('perm1', rules.always_true)
    add_perm('perm2', rules.always_true)
    add_perm('perm3', rules.always_false)
    role_registry.register('role1', ['perm1'])
    role_registry.register('role2', ['perm2'])
    user.roles = {'role1', 'role2'}
    assert user.has_perm('perm1')
    assert user.has_perm('perm2')
    assert not user.has_perm('perm3')