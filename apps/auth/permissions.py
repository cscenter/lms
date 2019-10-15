from abc import ABCMeta, abstractmethod
from typing import Type, Dict, Set, Optional, Iterable, Union, NewType

from rules import RuleSet, Predicate, always_true

from auth.errors import PermissionNotRegistered, AuthPermissionError

PermissionId = str


class Permission(metaclass=ABCMeta):
    @property
    @abstractmethod
    def name(self) -> PermissionId:
        raise NotImplementedError

    rule: Optional[Predicate] = None


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
                 # TODO: Change type to Iterable[Type[Permission]] after migrate
                 permissions: Iterable[Union[Type[Permission], PermissionId]],
                 relations: Dict = None):
        self.code = code
        self.name = name
        self._permissions: RuleSet = RuleSet()
        for perm in permissions:
            if isinstance(perm, str) and perm in perm_registry:
                perm = perm_registry[perm]
            if not issubclass(perm, Permission):
                raise TypeError(f"{perm} is not subclass of Permission")
            if perm.name not in perm_registry:
                msg = ("Permission `{}` is not added into global registry. "
                       "Call `auth.permissions.add_perm` first.".format(perm))
                raise PermissionNotRegistered(msg)
            pred = always_true if perm.rule is None else perm.rule
            self._permissions.add_rule(perm.name, pred)
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
        self._permissions.add_rule(perm.name, perm.rule)

    def has_permission(self, perm: Union[str, Type[Permission]]) -> bool:
        if isinstance(perm, str):
            return perm in self._permissions
        elif issubclass(perm, Permission):
            return perm.name in self._permissions
        return False

    @property
    def relations(self) -> Dict[PermissionId, Set[PermissionId]]:
        """
        relations хранит связи некоторых прав и используется для решения
        следующей ситуации:

        Предположим, у нас есть правило `update_assignment`. Т.к. оно слишком
        общее, мы его назначаем только куратору.
        Для преподавателя мы создаём правило `update_own_assignment` и
        дополнительно проверяем, что текущий авторизованный пользователь
        является преподавателем редактируемого задания.
        В коде это будет выглядеть как
        `user.has_perm('update_own_assignment', assignment)`
        Что если у нас есть ресурс, к которому нужно расшарить доступ и для преподавателя и для куратора?
        Нам придётся написать что-то вроде
        `user.has_perm('update_own_assignment', assignment) or user.has_perm('update_assignment')`
        Если появляется ещё одна роль, то мы добавляем новое условие OR.
        children помогает писать более общий код вида
        `user.has_perm('update_assignment', assignment)`
        Для куратора сразу будет возвращено True, для преподавателя
        children будет хранить связь `update_assignment` -> `update_own_assignment`
        """
        return self._relations

    def __repr__(self):
        return f"{self.__class__} [code: '{self.code}' name: {self.name}]"

    def add_relation(self, common_perm: Type[Permission],
                     specific_perm: Type[Permission]):
        """
        Add relation between two permissions.
        Example:
            # `user.has_perm('update_comment', object)` will call
            # `user.has_perm('update_own_comment', object)` if user has no
            # 'update_comment' permission, but has `role1` among roles
            role1.add_relation(UpdateComment, UpdateOwnComment)
        """
        parent: PermissionId = common_perm.name
        child: PermissionId = specific_perm.name
        if parent not in perm_registry:
            raise PermissionNotRegistered(f"{common_perm} is not registered")
        if child not in perm_registry:
            raise PermissionNotRegistered(f"{specific_perm} is not registered")
        if parent == child:
            raise AuthPermissionError(f"Cannot add {specific_perm} as a child of itself")
        if child not in self._permissions:
            raise PermissionNotRegistered(f"{specific_perm} is not registered in current role")

        # FIXME: detect loop
        if parent in self._relations and child in self._relations[parent]:
            raise AuthPermissionError(f"The item {common_perm} already has a "
                                      f"child permission {specific_perm}")
        if parent not in self._relations:
            self._relations[parent] = set()
        self._relations[parent].add(child)

    def has_relation(self, parent: Type[Permission], child: Type[Permission]):
        return parent.name in self._relations and child.name in self._relations[parent.name]
