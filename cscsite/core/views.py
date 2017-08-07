# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import io
import types

import datetime
from abc import abstractmethod, ABCMeta

import unicodecsv
from braces.views import UserPassesTestMixin, LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render_to_response
from django.utils.encoding import smart_text, python_2_unicode_compatible, \
    force_text
from django.views import generic
from vanilla import CreateView
from xlsxwriter import Workbook

from .utils import render_markdown


def robots(request):
    return render_to_response('robots.txt', content_type="text/plain")


# TODO: move mixins to separated module
class ReadOnlyFieldsMixin(object):
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


class LoginRequiredMixin(LoginRequiredMixin):
    raise_exception = False


class SuperUserOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return user.is_superuser


class ProtectedFormMixin(object):
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


@python_2_unicode_compatible
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

    # @method_decorator(requires_csrf_token)
    # def dispatch(self, *args, **kwargs):
    #     return super(MarkdownRenderView, self).dispatch(*args, **kwargs)


class ReportFileOutput(object):
    """Methods to output csv and xlsx"""
    headers = None
    data = None
    debug = False

    __metaclass__ = ABCMeta

    # TODO: Create base cls for ReportFile?
    @abstractmethod
    def export_row(self, row):
        raise NotImplementedError()

    def output_csv(self):
        output = io.BytesIO()
        w = unicodecsv.writer(output, encoding='utf-8')

        w.writerow(self.headers)
        for data_row in self.data:
            row = self.export_row(data_row)
            w.writerow(row)
        output.seek(0)
        response = HttpResponse(output.read(),
                                content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = \
            'attachment; filename="{}.csv"'.format(self.get_filename())

        if self.debug:
            return self.debug_response()

        return response

    def output_xlsx(self):
        output = io.BytesIO()
        workbook = Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        format = workbook.add_format()

        format.set_bold()
        for index, header in enumerate(self.headers):
            worksheet.write(0, index, header, format)

        format.set_bold(False)
        for row_index, raw_row in enumerate(self.data, start=1):
            row = self.export_row(raw_row)
            for col_index, value in enumerate(row):
                value = "" if value is None else force_text(value)
                worksheet.write(row_index, col_index, force_text(value), format)

        workbook.close()
        output.seek(0)
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        response = HttpResponse(output.read(), content_type=content_type)
        response['Content-Disposition'] = \
            'attachment; filename="{}.xlsx"'.format(self.get_filename())

        if self.debug:
            return self.debug_response()

        return response

    def get_filename(self):
        today = datetime.datetime.now()
        return "report_{}".format(today.strftime("%d.%m.%Y"))

    def debug_response(self):
        # TODO: replace with table view
        return HttpResponse("<html><body></body></html>",
                            content_type='text/html; charset=utf-8')


class MarkdownHowToHelpView(generic.TemplateView):
    template_name = "markdown_how_to.html"
