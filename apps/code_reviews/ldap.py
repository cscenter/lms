import base64
from typing import Optional

import ldif

from django.conf import settings
from django.utils.encoding import force_bytes

from code_reviews.constants import GROUPS_IMPORT_TO_GERRIT
from users.models import User


def get_ldap_username(user: User):
    """
    Portable Filename Character Set (according to POSIX.1-2017) is used for
    username since @ in a username can be misleading when you are connecting
    over ssh. `foo@localhost.ru@domain.ltd` really looks weird.
    """
    return user.email.replace("@", ".")


def get_password_hash(user) -> Optional[bytes]:
    """
    Converts Django's password hash representation to LDAP compatible
    hasher format. Supports pbkdf2 hasher only.
    """
    if not user.password:
        return b''
    # Could easily fail on tests since md5 hasher returns only 3 parameters
    algorithm, iterations, salt, hash = user.password.split('$', 3)
    if algorithm == "pbkdf2_sha256":
        ldap_hasher_code = "{PBKDF2-SHA256}"
    elif algorithm == "pbkdf2_sha512":
        ldap_hasher_code = "{PBKDF2-SHA512}"
    elif algorithm == "pbkdf2_sha1":
        ldap_hasher_code = "{PBKDF2-SHA1}"
    else:
        return b''
    # Works like `passlib.utils.binary.ab64_encode` except
    # converting "+" to "."
    ab64_salt = base64.b64encode(salt.encode("utf-8")).rstrip(b"=\n")
    h = f"{ldap_hasher_code}{iterations}${ab64_salt.decode('utf-8')}${hash}"
    return h.encode("utf-8")


def user_to_ldap_entry(user: User, domain_component=settings.LDAP_DB_SUFFIX):
    """
    Converts user object into LDIF entry.
    Notes:
        Each added attribute needs to be added as a list.
        Each value of this list should be forced to bytes except `dn`
            since it's not used as a part of `modlist`
    """
    uid = get_ldap_username(user)
    dn = f"uid={uid},ou=users,{domain_component}"
    password_hash = get_password_hash(user)
    return {
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


# FIXME: у некоторых пользователей нет пароля, надо их импортировать и посмотреть, создастся ли для них аккаунт и не будет ли там падать с 500й, если пробовать входить по пустому паролю или любому невалидному.
def export(file_path, site_id=settings.SITE_ID):
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
            ldif_writer = ldif.LDIFWriter(f)
            ldif_writer.unparse(user_dn, entry)
