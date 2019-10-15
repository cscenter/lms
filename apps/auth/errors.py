class AuthBaseError(Exception):
    pass


class AuthPermissionError(AuthBaseError):
    pass


class PermissionNotRegistered(AuthPermissionError):
    pass


class AlreadyRegistered(AuthBaseError):
    pass


class NotRegistered(AuthBaseError):
    pass
