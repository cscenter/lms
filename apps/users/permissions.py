import rules

from auth.permissions import Permission, add_perm
from users.models import User


@add_perm
class CreateCertificateOfParticipation(Permission):
    name = "users.create_certificate_of_participation"


@add_perm
class ViewCertificateOfParticipation(Permission):
    name = "users.view_certificate_of_participation"


@add_perm
class ViewAccountConnectedServiceProvider(Permission):
    name = "users.view_account_connected_service_provider"


@add_perm
class ViewOwnAccountConnectedServiceProvider(Permission):
    name = "users.view_own_account_connected_service_provider"

    @staticmethod
    @rules.predicate
    def rule(user, account: User):
        return user.is_authenticated and user == account


@rules.predicate
def is_curator(user):
    return user.is_superuser and user.is_staff
