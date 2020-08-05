from abc import ABCMeta, abstractmethod
from typing import Type, Dict, Set, Optional, Iterable, Union, NewType

from rest_framework.permissions import BasePermission
from rules import RuleSet, Predicate, always_true

from .errors import PermissionNotRegistered, AuthPermissionError

PermissionId = str


class Permission(BasePermission):
    @property
    @abstractmethod
    def name(self) -> PermissionId:
        raise NotImplementedError

    rule: Optional[Predicate] = None

    def has_permission(self, request, view) -> bool:
        """
        Django Rest Framework calls this for each view in `dispatch` method
        """
        return True

    def has_object_permission(self, request, view, obj) -> bool:
        """
        Will be called by DRF in `get_object` method.

        Some permissions implicitly considered as `always True` and
        haven't attached predicate rule
        """
        return request.user.has_perm(self.name, obj)


class PermissionRegistry:
    """
    This registry is used to avoid name collision in the permission name.
    """
    def __init__(self):
        self._dict: Dict[PermissionId, Permission] = {}

    def test_rule(self, name, *args, **kwargs) -> bool:
        return name in self._dict and self._dict[name].rule.test(*args, **kwargs)

    def add_permission(self, perm: Type[Permission]) -> None:
        if perm.name in self._dict:
            raise KeyError('A perm with name `%s` already exists' % perm.name)
        self._dict[perm.name] = perm

    def set_permission(self, perm: Type[Permission]) -> None:
        self._dict[perm.name] = perm

    def remove_permission(self, perm) -> None:
        if isinstance(perm, PermissionId):
            del self._dict[perm]
        else:
            del self._dict[perm.name]

    def __contains__(self, perm) -> bool:
        if isinstance(perm, PermissionId):
            return perm in self._dict
        return perm.name in self._dict

    def __getitem__(self, perm_name) -> Permission:
        return self._dict[perm_name]


perm_registry = PermissionRegistry()


def add_perm(cls: Type[Permission]) -> Type[Permission]:
    perm_registry.add_permission(cls)
    return cls


class Role:
    def __init__(self, *, code, name,
                 permissions: Iterable[Type[Permission]],
                 priority: int = 100,
                 relations: Dict = None):
        self.code = code
        self.name = name
        # `User.has_perm(...)` iterates over permissions (grouped by role)
        # until the first successful match by name, eval the permission
        # callback and returns the result.
        # It could lead to the false negative if 2 roles has the same permission
        # name (see `Role.relations` description for the details)
        # To avoid this auth backend should check permissions of the most
        # priority roles first.
        self.priority = priority  # The less value the higher priority
        self._permissions: RuleSet = RuleSet()
        for perm in permissions:
            if not issubclass(perm, Permission):
                raise TypeError(f"{perm} is not subclass of Permission")
            self.add_permission(perm)
        self._relations: Dict[PermissionId, Set[PermissionId]] = {}
        relations = relations or {}
        for parent, child in relations.items():
            self.add_relation(parent, child)

    @property
    def permissions(self) -> RuleSet:
        return self._permissions

    def add_permission(self, perm: Type[Permission]) -> None:
        if perm.name not in perm_registry:
            msg = ("Permission `{}` is not added into global registry. "
                   "Call `auth.permissions.add_perm` first.".format(perm))
            raise PermissionNotRegistered(msg)
        pred = always_true if perm.rule is None else perm.rule
        self._permissions.add_rule(perm.name, pred)

    def has_permission(self, perm: Union[str, Type[Permission]]) -> bool:
        if isinstance(perm, str):
            return perm in self._permissions
        elif issubclass(perm, Permission):
            return perm.name in self._permissions
        return False

    @property
    def relations(self) -> Dict[PermissionId, Set[PermissionId]]:
        """
        Some shared resources require different permissions level, e.g.
        curator always could edit assignment while teacher could edit only
        assignments where they participated. In that case we should apply
        additional rule to teacher permission. On code level permission check
        will look like:

            # Curator
            if (user.has_perm('edit_assignment') or
                    # Teacher
                    user.has_perm('edit_own_assignment', assignment_obj)):
                ...

        If we added new role that have access to the shared resource
        we should edit this code. To avoid this complexity let's generalize
        permission check to:

            # For curator, teacher or other roles
            user.has_perm('edit_assignment', assignment_obj)

        In case user has no `edit_assignment` permission we additionally
        check relation chain, e.g. `edit_assignment -> edit_own_assignment`,
        where `edit_own_assignment` has custom permission rule applied to it
        """
        return self._relations

    def __repr__(self):
        return f"{self.__class__} [code: '{self.code}' name: {self.name}]"

    def add_relation(self, common_perm: Type[Permission],
                     specific_perm: Type[Permission]):
        """
        Add relation between two permissions.
        Example:
            `user.has_perm('update_comment', object)` will call
            `user.has_perm('update_own_comment', object)` if user has no
            'update_comment' permission, but has role with relation
            .add_relation(UpdateComment, UpdateOwnComment)
        """
        parent = common_perm.name
        child = specific_perm.name
        if parent not in perm_registry:
            raise PermissionNotRegistered(f"{common_perm} is not registered")
        if child not in perm_registry:
            raise PermissionNotRegistered(f"{specific_perm} is not registered")
        if parent == child:
            raise AuthPermissionError(f"Cannot add {specific_perm} as a child of itself")
        if child not in self._permissions:
            raise PermissionNotRegistered(f"{specific_perm} is not registered in a current role")
        # FIXME: child must be object level permission only!
        # FIXME: detect loop
        if parent in self._relations and child in self._relations[parent]:
            raise AuthPermissionError(f"The item {common_perm} already has a "
                                      f"child permission {specific_perm}")
        if parent not in self._relations:
            self._relations[parent] = set()
        self._relations[parent].add(child)

    def has_relation(self, parent: Type[Permission], child: Type[Permission]):
        return parent.name in self._relations and child.name in self._relations[parent.name]
