# -*- coding: utf-8 -*-

import types

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse
from django.utils.encoding import smart_text
from django.views import generic
from vanilla import CreateView

from core.models import Branch
from .utils import render_markdown


class RequestBranchMixin:
    """
    This view mixin sets `branch` attribute to request object based on
    `request.site` and non-empty `branch_code` view keyword argument
    """
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        branch_code = kwargs.get("branch_code", None)
        if not branch_code:
            raise ImproperlyConfigured(
                f"{self.__class__} is subclass of RequestBranchMixin but "
                f"`branch_code` view keyword argument is not specified or empty")
        request.branch = Branch.objects.get_by_natural_key(branch_code,
                                                           request.site.id)


class ReadOnlyFieldsMixin:
    readonly_fields = ()

    def __init__(self, *args, **kwargs):
        super(ReadOnlyFieldsMixin, self).__init__(*args, **kwargs)
        for field in (field for name, field in self.fields.items()
                      if self._pred(name)):
            field.widget.attrs['disabled'] = 'true'
            field.required = False

    def _pred(self, field_name):
        if self.readonly_fields == "__all__":
            return True
        return field_name in self.readonly_fields

    def clean(self):
        cleaned_data = super(ReadOnlyFieldsMixin,self).clean()
        for field in self.readonly_fields:
            cleaned_data[field] = getattr(self.instance, field)
        return cleaned_data


class ProtectedFormMixin:
    def __init__(self, *args, **kwargs):
        self._cached_object = None
        # Note(lebedev): no point in calling 'super' here.
        super(ProtectedFormMixin, self).__init__(*args, **kwargs)

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
        if isinstance(self, (generic.edit.BaseCreateView, CreateView)):
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
            return redirect_to_login(request.get_full_path())
        else:
            return (super(ProtectedFormMixin, self)
                    .dispatch(request, *args, **kwargs))


class MarkdownRenderView(LoginRequiredMixin, generic.base.View):
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        if 'text' not in request.POST:
            return JsonResponse({'status': 'ERROR', 'text': 'empty request'})
        text = smart_text(request.POST['text'])
        rendered_text = render_markdown(text)
        return JsonResponse({'status': 'OK', 'text': rendered_text})

    def __str__(self):
        return ''


class MarkdownHowToHelpView(generic.TemplateView):
    template_name = "markdown_how_to.html"
