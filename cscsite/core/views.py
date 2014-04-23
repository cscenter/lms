import types

from django.core.exceptions import PermissionDenied
from django.views import generic

from braces.views import UserPassesTestMixin


class StudentOnlyMixin(UserPassesTestMixin):
    def test_func(self, user):
        return user.is_authenticated() and user.is_student


class TeacherOnlyMixin(UserPassesTestMixin):
    def test_func(self, user):
        return user.is_authenticated() and user.is_teacher


class StaffOnlyMixin(UserPassesTestMixin):
    def test_func(self, user):
        return user.is_staff


class ProtectedFormMixin(object):
    def is_form_allowed(self, user, obj):
        raise NotImplementedError(
            "{0} is missing implementation of the "
            "is_form_allowed(self, user, obj) method. "
            "You should write one.".format(
                self.__class__.__name__))

    def dispatch(self, request, *args, **kwargs):
        # This is needed because BaseCreateView doesn't call get_object,
        # setting self.object to None instead. Of course, this hack is fragile,
        # but, anyway, it will crash instead of letting do wrong things.
        if isinstance(self, generic.edit.BaseCreateView):
            obj = None
        else:
            obj = self._cached_object = self.get_object()
        # This is a very hacky monkey-patching to avoid refetching of object
        # inside BaseUpdateView's get/post.

        def _temp_get_object(inner_self, qs=None):
            if qs is None:
                return inner_self._cached_object
            else:
                return self.get_object(qs)
        setattr(self, "get_object",
                types.MethodType(_temp_get_object, self))
        if not self.is_form_allowed(request.user, obj):
            raise PermissionDenied
        else:
            return (super(ProtectedFormMixin, self)
                    .dispatch(request, *args, **kwargs))
