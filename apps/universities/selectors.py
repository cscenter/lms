from typing import Any, Dict, Optional

from django_filters import NumberFilter
from django_filters.rest_framework import FilterSet
from rest_framework.exceptions import ValidationError

from django.db.models import QuerySet

from universities.models import Faculty, University


class UniversityFilter(FilterSet):
    city = NumberFilter(lookup_expr='exact', required=False)

    class Meta:
        model = University
        fields = ('city',)


def universities_queryset(*, filters: Optional[Dict[str, Any]] = None) -> QuerySet[University]:
    filter_set = UniversityFilter(filters, University.objects.get_queryset())
    if filter_set.is_bound and not filter_set.is_valid():
        raise ValidationError(filter_set.errors)
    return filter_set.qs.order_by()


class FacultyFilter(FilterSet):
    university = NumberFilter(lookup_expr='exact', required=False)

    class Meta:
        model = Faculty
        fields = ('university',)


def faculties_queryset(*, filters: Optional[Dict[str, Any]] = None) -> QuerySet[Faculty]:
    filter_set = FacultyFilter(filters, Faculty.objects.get_queryset())
    if filter_set.is_bound and not filter_set.is_valid():
        raise ValidationError(filter_set.errors)
    return filter_set.qs.order_by()
