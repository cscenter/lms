from auth.registry import role_registry
from users.permissions import (
    ViewAccountConnectedServiceProvider, ViewOwnAccountConnectedServiceProvider
)

authenticated_role = role_registry.authenticated_role
authenticated_role.add_permission(ViewOwnAccountConnectedServiceProvider)
authenticated_role.add_relation(ViewAccountConnectedServiceProvider,
                                ViewOwnAccountConnectedServiceProvider)
