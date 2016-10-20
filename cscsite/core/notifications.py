from threading import local

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property


_thread_locals = local()
_installed_middleware = False


def get_unread_notifications_cache():
    if not _installed_middleware:
        raise ImproperlyConfigured(
            "NotificationsCacheMiddleware not loaded")
    assert _thread_locals.unread_notifications_cache, \
        "NotificationsCache isn't initialized. Is user logged in?"
    return _thread_locals.unread_notifications_cache


class UnreadNotificationsCache(object):
    def __init__(self, assignments_qs, coursenews_qs):
        assert assignments_qs is not None
        assert coursenews_qs is not None
        self.assignments_qs = assignments_qs
        self.coursenews_qs = coursenews_qs

    @cached_property
    def assignments(self):
        return {obj.student_assignment: obj
                for obj in self.assignments_qs.all()}

    @cached_property
    def assignments_student(self):
        return {a_s: obj
                for a_s, obj in self.assignments.items()
                if a_s.student_id == obj.user.id}

    @cached_property
    def assignments_teacher(self):
        return {a_s: obj
                for a_s, obj in self.assignments.items()
                if a_s.student_id != obj.user.id}

    @cached_property
    def assignment_ids_set(self):
        return {a_s.assignment_id for a_s in self.assignments}

    @cached_property
    def courseoffering_news(self):
        return {obj.course_offering_news.course_offering: obj
                for obj in self.coursenews_qs.all()}


class UnreadNotificationsCacheMiddleware(object):
    def __init__(self):
        global _installed_middleware
        _installed_middleware = True

    def process_request(self, request):
        # FIXME: Don't know what is the point to save cache in _thread_locals
        # when it's unique for each request
        _thread_locals.unread_notifications_cache = None
        if request.user.is_authenticated():
            cache = UnreadNotificationsCache(
                (request.user
                 .assignmentnotification_set
                 .filter(is_unread=True)
                 .select_related('student_assignment')),
                (request.user
                 .courseofferingnewsnotification_set
                 .filter(is_unread=True)
                 .select_related('course_offering_news',
                                 'course_offering_news__course_offering')))
            _thread_locals.unread_notifications_cache = cache
            setattr(request, 'unread_notifications_cache', cache)
