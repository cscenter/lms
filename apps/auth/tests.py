import pytest
import rules

from auth.backends import RBACModelBackend, RBACPermissions
from auth.permissions import add_perm, perm_registry, Permission, Role
from auth.registry import role_registry, role_registry
from users.tests.factories import UserFactory
from .errors import AlreadyRegistered, PermissionNotRegistered


class Permission1(Permission):
    name = 'test_permission1'

    @staticmethod
    @rules.predicate
    def rule(user, obj):
        return obj == 42


class PermissionAlwaysTrue(Permission):
    name = 'test_permission2'


class Permission3(Permission):
    name = 'test_permission3'

    @staticmethod
    @rules.predicate
    def rule(user, obj):
        return obj == 11


def test_permission_registry(mocker):
    mocker.patch.dict(perm_registry._dict, clear=True)
    perm_registry.add_permission(Permission1)
    assert Permission1 in perm_registry
    assert Permission1.name in perm_registry
    assert perm_registry.test_rule(Permission1.name, None, 42)
    assert not perm_registry.test_rule(Permission1.name, None, 43)
    with pytest.raises(KeyError):
        perm_registry.add_permission(Permission1)
    perm_registry.remove_permission(Permission1)
    perm_registry.set_permission(Permission1)


def test_role(mocker):
    mocker.patch.dict(perm_registry._dict, clear=True)
    perm_registry.add_permission(Permission1)
    with pytest.raises(PermissionNotRegistered):
        role = Role(code=1, name="TestRole", permissions=(PermissionAlwaysTrue,))
    role = Role(code=1, name="TestRole", permissions=(Permission1,))
    assert role.has_permission(Permission1)
    assert not role.has_permission(PermissionAlwaysTrue)
    with pytest.raises(PermissionNotRegistered):
        role.add_permission(PermissionAlwaysTrue)


def test_role_relations(mocker):
    mocker.patch.dict(perm_registry._dict, clear=True)
    perm_registry.add_permission(Permission1)
    role = Role(code=1, name="TestRole", permissions=(Permission1,))
    # TestPermission2 is not registered in global registry
    with pytest.raises(PermissionNotRegistered):
        role.add_relation(Permission1, PermissionAlwaysTrue)
    perm_registry.add_permission(PermissionAlwaysTrue)
    # TestPermission2 is not a part of current role permissions set
    with pytest.raises(PermissionNotRegistered):
        role.add_relation(Permission1, PermissionAlwaysTrue)
    role.add_permission(PermissionAlwaysTrue)
    role.add_relation(Permission1, PermissionAlwaysTrue)
    assert role.has_relation(Permission1, PermissionAlwaysTrue)
    assert not role.has_relation(PermissionAlwaysTrue, Permission1)


@pytest.mark.django_db
def test_backend(mocker):
    mocker.patch.dict(role_registry._registry, clear=True)
    mocker.patch.dict(perm_registry._dict, clear=True)
    backend = RBACModelBackend()
    user = UserFactory()
    assert not backend.has_perm(user, PermissionAlwaysTrue.name)
    perm_registry.add_permission(PermissionAlwaysTrue)
    role1 = Role(code='role', name="TestRole1",
                 permissions=(PermissionAlwaysTrue,))
    role_registry.register(role1)
    assert not user.has_perm(PermissionAlwaysTrue.name)
    user.roles = ['role']
    assert user.has_perm(PermissionAlwaysTrue.name)


@pytest.mark.django_db
def test_rbac_backend_has_perm(mocker):
    mocker.patch.dict(role_registry._registry, clear=True)
    mocker.patch.dict(perm_registry._dict, clear=True)
    perm_registry.add_permission(Permission1)
    perm_registry.add_permission(PermissionAlwaysTrue)
    perm_registry.add_permission(Permission3)
    role1 = Role(code='role1', name="TestRole1",
                 permissions=(Permission1,))
    role_registry.register(role1)
    role2 = Role(code='role2', name="TestRole2",
                 permissions=(PermissionAlwaysTrue,))
    role_registry.register(role2)
    user = UserFactory()
    user.roles = {'role1', 'role2'}
    assert not RBACPermissions().has_perm(user, 'test_permission1')
    assert RBACPermissions().has_perm(user, 'test_permission1', 42)
    assert RBACPermissions().has_perm(user, 'test_permission2')
    # No need to pass an object since we didn't find a permission
    # binded to user roles
    assert not RBACPermissions().has_perm(user, 'test_permission3')
    # Test relations
    role1.add_relation(Permission3, Permission1)
    assert not RBACPermissions().has_perm(user, 'test_permission3', 11)
    assert RBACPermissions().has_perm(user, 'test_permission3', 42)
    # assert not RBACPermissions2().has_perm(user, 'test_permission3', 12)
