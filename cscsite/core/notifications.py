from threading import local

from django.contrib.auth import get_user_model
from django.utils.functional import cached_property


_thread_locals = local()
_installed_middleware = False


def get_unread_notifications_cache():
    assert _installed_middleware, "NotificationsCacheMiddleware not loaded"
    assert _thread_locals.unread_notifications_cache, \
        "NotificationsCache isn't initialized. Is user logged in?"
    return _thread_locals.unread_notifications_cache


class UnreadNotificationsCache(object):
    def __init__(self, assignments_qs):
        assert assignments_qs is not None
        self.assignments_qs = assignments_qs

    @cached_property
    def assignments(self):
        return {obj.assignment_student: obj
                for obj in self.assignments_qs.all()}


class UnreadNotificationsCacheMiddleware(object):
    def __init__(self):
        global _installed_middleware
        _installed_middleware = True

    def process_request(self, request):
        _thread_locals.unread_notifications_cache = None
        if request.user.is_authenticated():
            cache = UnreadNotificationsCache(
                (request.user
                 .assignmentnotification_set
                 .filter(is_unread=True)))
            _thread_locals.unread_notifications_cache = cache
            setattr(request, 'unread_notifications_cache', cache)
