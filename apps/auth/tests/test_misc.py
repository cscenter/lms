import pytest
import rules

from auth.backends import RBACModelBackend, RBACPermissions
from auth.errors import PermissionNotRegistered
from auth.permissions import Permission, Role, perm_registry
from auth.registry import role_registry
from users.tests.factories import UserFactory


class Permission1(Permission):
    name = 'test_permission1'
    VALID_VALUE = 42
    INVALID_VALUE = 43

    @staticmethod
    @rules.predicate
    def rule(user, obj):
        return obj == 42


class PermissionReturnsTrue(Permission):
    name = 'test_permission2'


class PermissionReturnsFalse(Permission):
    name = 'test_permission3'

    @staticmethod
    @rules.predicate
    def rule(user, obj):
        return False


class Permission3(Permission):
    name = 'test_permission4'
    VALID_VALUE = 11
    INVALID_VALUE = 12

    @staticmethod
    @rules.predicate
    def rule(user, obj):
        return obj == Permission3.VALID_VALUE


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
        role = Role(id=1, code='1', description="TestRole", permissions=(PermissionReturnsTrue,))
    role = Role(id=1, code='1', description="TestRole", permissions=(Permission1,))
    assert role.has_permission(Permission1)
    assert not role.has_permission(PermissionReturnsTrue)
    with pytest.raises(PermissionNotRegistered):
        role.add_permission(PermissionReturnsTrue)


def test_role_relations(mocker):
    mocker.patch.dict(perm_registry._dict, clear=True)
    perm_registry.add_permission(Permission1)
    role = Role(id=1, description="TestRole", permissions=(Permission1,))
    # TestPermission2 is not registered in global registry
    with pytest.raises(PermissionNotRegistered):
        role.add_relation(Permission1, PermissionReturnsTrue)
    perm_registry.add_permission(PermissionReturnsTrue)
    # TestPermission2 is not a part of current role permissions set
    with pytest.raises(PermissionNotRegistered):
        role.add_relation(Permission1, PermissionReturnsTrue)
    role.add_permission(PermissionReturnsTrue)
    role.add_relation(Permission1, PermissionReturnsTrue)
    assert role.has_relation(Permission1, PermissionReturnsTrue)
    assert not role.has_relation(PermissionReturnsTrue, Permission1)


@pytest.mark.django_db
def test_backend(mocker):
    mocker.patch.dict(role_registry._registry, clear=True)
    mocker.patch.dict(perm_registry._dict, clear=True)
    role_registry._register_default_roles()
    backend = RBACModelBackend()
    user = UserFactory()
    assert not backend.has_perm(user, PermissionReturnsTrue.name)
    perm_registry.add_permission(PermissionReturnsTrue)
    role1 = Role(id='role', description="TestRole1", priority=10,
                 permissions=(PermissionReturnsTrue,))
    role_registry.register(role1)
    assert not user.has_perm(PermissionReturnsTrue.name)
    user.roles = ['role']
    assert user.has_perm(PermissionReturnsTrue.name)


@pytest.mark.django_db
def test_rbac_backend_has_perm(mocker):
    mocker.patch.dict(role_registry._registry, clear=True)
    mocker.patch.dict(perm_registry._dict, clear=True)
    role_registry._register_default_roles()
    perm_registry.add_permission(Permission1)
    perm_registry.add_permission(PermissionReturnsTrue)
    perm_registry.add_permission(Permission3)
    role1 = Role(id='role1', description="TestRole1", priority=10,
                 permissions=(Permission1,))
    role_registry.register(role1)
    role2 = Role(id='role2', description="TestRole2", priority=11,
                 permissions=(PermissionReturnsTrue,))
    role_registry.register(role2)
    user = UserFactory()
    user.roles = {'role1', 'role2'}
    assert not RBACPermissions().has_perm(user, 'test_permission1')
    assert RBACPermissions().has_perm(user, 'test_permission1', 42)
    assert RBACPermissions().has_perm(user, 'test_permission2')
    # No need to pass an object since we didn't find a permission
    # binded to user roles
    assert not RBACPermissions().has_perm(user, Permission3.name)
    # Test relations
    role1.add_relation(Permission3, Permission1)
    assert not RBACPermissions().has_perm(user, Permission3.name, 11)
    assert RBACPermissions().has_perm(user, Permission3.name, 42)


@pytest.mark.django_db
def test_rbac_backend_has_perm_role_priority(mocker):
    mocker.patch.dict(role_registry._registry, clear=True)
    mocker.patch.dict(perm_registry._dict, clear=True)
    role_registry._register_default_roles()
    perm_registry.add_permission(Permission1)
    perm_registry.add_permission(PermissionReturnsTrue)
    perm_registry.add_permission(PermissionReturnsFalse)
    perm_registry.add_permission(Permission3)
    role1 = Role(id='role1', description="TestRole1", priority=30,
                 permissions=[PermissionReturnsFalse])
    role2 = Role(id='role2', description="TestRole2", priority=20,
                 permissions=[PermissionReturnsTrue])
    role1.add_relation(Permission1, PermissionReturnsFalse)
    role1.add_relation(Permission3, PermissionReturnsFalse)
    role2.add_relation(Permission1, PermissionReturnsTrue)
    role_registry.register(role1)
    role_registry.register(role2)
    user = UserFactory()
    user.roles = {'role1', 'role2'}
    # role2 has higher priority than role1
    assert RBACPermissions().has_perm(user, Permission1.name, Permission1.INVALID_VALUE)
    role3 = Role(id='role3', description="TestRole3", priority=10,
                 permissions=[Permission3])
    role_registry.register(role3)
    user.roles = {'role1', 'role2'}
    # Check PermissionReturnsFalse predicate
    assert not RBACPermissions().has_perm(user, Permission3.name, Permission3.VALID_VALUE)
    user.roles = {'role1', 'role2', 'role3'}
    # role3.priority > role1.priority => check Permission3 predicate
    assert RBACPermissions().has_perm(user, Permission3.name, Permission3.VALID_VALUE)
