import logging
from abc import ABCMeta, abstractmethod
from collections import defaultdict

from django.utils.translation import ugettext_noop

from users.models import UserGroup, User

logger = logging.getLogger(__name__)

# A list of registered access roles.
REGISTERED_ACCESS_ROLES = {}

# FIXME: remove?

def register_access_role(cls):
    """
    Decorator that allows access roles to be registered within the groups
    module and referenced by their string values.
    Assumes that the decorated class has a "ROLE" attribute, defining its type.
    """
    try:
        role_name = cls.ROLE
        REGISTERED_ACCESS_ROLES[role_name] = cls
    except AttributeError:
        logger.exception(f"Unable to register Access Role with class {cls}.")
    return cls


class RoleCache:
    """
    A cache of the AccessRoles held by a particular user
    """
    CACHE_NAMESPACE = "users.roles.RoleCache"
    CACHE_KEY = "roles_by_user"

    def __init__(self, user):
        try:
            self._roles = RoleCache.get_user_roles(user)
        except KeyError:
            self._roles = set(UserGroup.objects.filter(user=user).all())

    @classmethod
    def prefetch(cls, users):
        roles_by_user = defaultdict(set)
        get_cache(cls.CACHE_NAMESPACE)[cls.CACHE_KEY] = roles_by_user

        roles = (UserGroup.objects
                 .filter(user__in=users)
                 .select_related('user'))
        for role in roles:
            roles_by_user[role.user.id].add(role)

        users_without_roles = filter(lambda u: u.id not in roles_by_user, users)
        for user in users_without_roles:
            roles_by_user[user.id] = set()

    @classmethod
    def get_user_roles(cls, user):
        return get_cache(cls.CACHE_NAMESPACE)[cls.CACHE_KEY][user.id]

    def has_role(self, role, site_id):
        """
        Return whether this RoleCache contains a role with
        the specified role, course_id, and site.
        """
        return any(access_role.role == role and access_role.site_id == site_id
                   for access_role in self._roles)


class AccessRole:
    """
    Object representing a role with particular access to a resource
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def has_user(self, user):
        """
        Return whether the supplied django user has access to this role.
        """
        return False

    @abstractmethod
    def add_users(self, *users):
        """
        Add the role to the supplied django users.
        """
        pass

    @abstractmethod
    def remove_users(self, *users):
        """
        Remove the role from the supplied django users.
        """
        pass

    @abstractmethod
    def users_with_role(self):
        """
        Return a django QuerySet for all of the users with this role
        """
        return User.objects.none()


class Curator(AccessRole):
    """
    The global staff role. Allows to access the admin section.
    """
    def has_user(self, user):
        return user.is_superuser

    def add_users(self, *users):
        for user in users:
            if user.is_active:
                user.is_superuser = True
                user.save()

    def remove_users(self, *users):
        for user in users:
            user.is_superuser = False
            user.save()

    def users_with_role(self):
        raise Exception("This operation is un-indexed, and shouldn't be used")


class RoleBase(AccessRole):
    """
    Roles by type (e.g., teacher, beta_user) and site
    """
    # FIXME: use role_id instead
    def __init__(self, role_name: str, site_id: int):
        """
        Create role from required role_name and site.
        """
        super(RoleBase, self).__init__()
        self._site_id = site_id
        self._role_name = role_name

    # pylint: disable=arguments-differ
    def has_user(self, user, check_user_activation=True) -> bool:
        """
        Check if the supplied django user has access to this role.
        Returns True if user has that particular role.

        Arguments:
            user: user to check against access to role
            check_user_activation: Indicating whether or not we need to check
                user activation while checking user roles
        """
        if check_user_activation and not (user.is_authenticated
                                          and user.is_active):
            return False

        if not hasattr(user, '_roles'):
            # Cache a list of roles that a user has.
            user._roles = RoleCache(user)

        return user._roles.has_role(self._role_name, self._site_id)

    def add_users(self, *users):
        """
        Add the supplied django users to this role.
        """
        # silently ignores anonymous and inactive users so that any that are
        # legit get updated.
        for u in users:
            if u.is_authenticated and u.is_active and not self.has_user(u):
                entry = UserGroup(user=u,
                                  role=self._role_name,
                                  site_id=self._site_id)
                entry.save()
                if hasattr(u, '_roles'):
                    # TODO: add to cache instead
                    del u._roles

    def remove_users(self, *users):
        """
        Remove the supplied django users from this role.
        """
        entries = (UserGroup.objects
                   .filter(user__in=users,
                           role=self._role_name,
                           site_id=self._site_id))
        entries.delete()
        for user in users:
            if hasattr(user, '_roles'):
                # TODO: remove from cache instead
                del user._roles

    def users_with_role(self):
        """
        Return a django QuerySet for all of the users with this role
        """
        filters = {
            "group__role": self._role_name,
            "group__site_id": self._site_id
        }
        # FIXME: .has_role
        return User.objects.filter(**filters)


class CourseRole(RoleBase):
    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


class AdmissionRole(RoleBase):
    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


class ProjectRole(RoleBase):
    def __init__(self, *args, **kwargs):
        super().__init__(self.ROLE, *args, **kwargs)


@register_access_role
class Student(CourseRole):
    ROLE = "student"
    verbose_name = ugettext_noop("Student")


@register_access_role
class Teacher(CourseRole):
    ROLE = "teacher"
    verbose_name = ugettext_noop("Teacher")


@register_access_role
class Graduate(CourseRole):
    ROLE = "graduate"
    verbose_name = ugettext_noop("Graduate")


@register_access_role
class Volunteer(CourseRole):
    ROLE = "volunteer"
    verbose_name = ugettext_noop("Volunteer")


@register_access_role
class Interviewer(AdmissionRole):
    ROLE = "interviewer"
    verbose_name = ugettext_noop("Interviewer")


# @register_access_role
class BetaTester(CourseRole):
    ROLE = "beta_tester"
    verbose_name = ugettext_noop("Beta Tester")


@register_access_role
class Curator(ProjectRole):
    ROLE = "project_curator"
    verbose_name = ugettext_noop("Curator of projects")


@register_access_role
class Reviewer(ProjectRole):
    ROLE = "project_reviewer"
    verbose_name = ugettext_noop("Project Reviewer")
