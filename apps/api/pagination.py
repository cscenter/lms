from rest_framework import pagination
from rest_framework.response import Response

from django.core.paginator import EmptyPage


class StandardPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

    def get_paginated_response(self, data):
        try:
            previous_page_number = self.page.previous_page_number()
        except EmptyPage:
            previous_page_number = None

        try:
            next_page_number = self.page.next_page_number()
        except EmptyPage:
            next_page_number = None

        return Response({
            'pagination': {
                'previous_page': previous_page_number,
                'next_page': next_page_number,
                'total_entries': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'page': self.page.number,
            },
            'results': data,
        })
