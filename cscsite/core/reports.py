import io
from abc import ABCMeta, abstractmethod
from datetime import datetime

import unicodecsv
from django.conf import settings
from django.http import HttpResponse
from django.utils import formats
from django.utils.encoding import force_text
from xlsxwriter import Workbook


class ReportFileOutput(object):
    """Methods to output csv and xlsx"""
    headers = None
    data = None

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

        # if settings.DEBUG:
        #     return self.debug_response(output.read())

        response = HttpResponse(output.read(),
                                content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = \
            'attachment; filename="{}.csv"'.format(self.get_filename())

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

        if settings.DEBUG:
            return self.debug_response()

        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        response = HttpResponse(output.read(), content_type=content_type)
        response['Content-Disposition'] = \
            'attachment; filename="{}.xlsx"'.format(self.get_filename())

        return response

    def get_filename(self):
        today = formats.date_format(datetime.now(), "SHORT_DATE_FORMAT")
        return f"report_{today}"

    def debug_response(self, output=b""):
        # TODO: replace with table view
        output = output.decode("utf-8")
        return HttpResponse(f"<html><body>{output}</body></html>",
                            content_type='text/html; charset=utf-8')
