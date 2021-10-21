import base64
import logging
from typing import Dict, List, Union

from ldap.dn import escape_dn_chars
from ldif import LDIFWriter

from django.conf import settings
from django.utils.encoding import force_bytes

from auth.models import ConnectedAuthService
from code_reviews.api.ldap import LDAPClient, adapted_base64
from code_reviews.gerrit.constants import GROUPS_IMPORT_TO_GERRIT
from users.models import User

logger = logging.getLogger(__name__)


def connect_gerrit_auth_provider(client, user: User) -> bool:
    """
    Creates LDAP account and associates gerrit auth provider with the user.
    """
    uid = get_ldap_username(user)
    associated = (ConnectedAuthService.objects
                  .filter(user=user, provider='gerrit', uid=uid)
                  .first())
    if associated is not None:
        logger.info(f"LDAP account already connected for user {user.pk}.")
        return False
    results = client.search_users(uid)
    if results:
        logger.info(f"LDAP entry with uid={uid} for user {user.pk} already exists")
        created = False
    else:
        logger.info(f"Creating LDAP entry with uid={uid} for user {user.pk}")
        entry = user_to_ldap_entry(user)
        result_type, *_ = client.add_entry(entry)
        created = True
    if created:
        # TODO: Create gerrit account here and save account uid in extra data
        connected = ConnectedAuthService(user=user, provider='gerrit', uid=uid)
        connected.save()
    return created


def update_ldap_user_password_hash(client: LDAPClient, user: User) -> bool:
    username = get_ldap_username(user)
    password_hash = get_ldap_password_hash(user.password)
    if not password_hash:
        logger.warning(f"Empty hash for user_id={user.pk}")
        return False
    changed = client.set_password_hash(username, password_hash)
    return bool(changed)


def get_ldap_username(user: User) -> str:
    """
    Portable Filename Character Set (according to POSIX.1-2017) is used for
    username since @ in a username can be misleading when you are connecting
    over ssh. `foo@localhost.ru@domain.ltd` really looks weird.
    """
    return user.email.replace("@", ".")


def get_ldap_password_hash(password_hash: str) -> bytes:
    """
    Converts Django's password hash representation to LDAP compatible
    hasher format. Supports pbkdf2 hasher only.
    """
    if not password_hash:
        return b''
    # Could easily fail on tests since md5 hasher returns only 3 parameters
    algorithm, iterations, salt, digest = password_hash.split('$', 3)
    if algorithm == "pbkdf2_sha256":
        ldap_hasher_code = "{PBKDF2-SHA256}"
    elif algorithm == "pbkdf2_sha512":
        ldap_hasher_code = "{PBKDF2-SHA512}"
    elif algorithm == "pbkdf2_sha1":
        ldap_hasher_code = "{PBKDF2-SHA1}"
    else:
        return b''
    adapted_salt = adapted_base64(salt.encode("utf-8")).decode('ascii')
    # Digest key is already base64 encoded, decode it first
    raw_digest = base64.b64decode(digest)
    adapted_hash = adapted_base64(raw_digest).decode('ascii')
    h = f"{ldap_hasher_code}{iterations}${adapted_salt}${adapted_hash}"
    return h.encode("utf-8")


def user_to_ldap_entry(user: User, domain_component=settings.LDAP_DB_SUFFIX) -> Dict[str, List[Union[bytes, str]]]:
    """
    Generates LDIF entry from the user object. Attribute values of the
    *domain_component* must be escaped.

    Notes:
        Each attribute needs to be added as a list.
        Each value of the list should be forced to bytes except `dn`
            since it's not used as a part of a `modlist`
    """
    uid = get_ldap_username(user)
    # Attribute values of the DN should be escaped
    dn = f"uid={escape_dn_chars(uid)},ou=users,{domain_component}"
    password_hash = get_ldap_password_hash(user.password)
    return {
        # Escape special chars with one backslash
        'dn': dn,
        'objectClass': [b'inetOrgPerson', b'simpleSecurityObject'],
        'uid': [force_bytes(uid)],
        'employeeNumber': [force_bytes(user.pk)],
        'sn': [force_bytes(user.last_name or user.username)],
        # Common name (or CN) is used as a branch name in a project git repo
        'cn': [force_bytes(user.get_abbreviated_name_in_latin())],
        'displayName': [force_bytes(user.get_short_name())],
        'mail': [force_bytes(user.email)],
        'userPassword': [password_hash]
    }


# FIXME: у некоторых пользователей нет пароля, надо их импортировать и
#  посмотреть, создастся ли для них аккаунт и не будет ли там падать с 500й,
#  если пробовать входить по пустому паролю или любому невалидному.
def export(file_path, site_id=settings.SITE_ID) -> None:
    """
    Exports account data in a LDIF format for users having at least one
    of the **GROUPS_IMPORT_TO_GERRIT** groups.
    Example:
        export("/path/to/dir/230320.ldif")
    """
    with open(file_path, 'w') as f:
        users = (User.objects
                 .has_role(*GROUPS_IMPORT_TO_GERRIT, site_id=site_id)
                 .distinct())
        for user in users:
            entry = user_to_ldap_entry(user)
            user_dn = entry.pop('dn')
            ldif_writer = LDIFWriter(f)
            ldif_writer.unparse(user_dn, entry)
