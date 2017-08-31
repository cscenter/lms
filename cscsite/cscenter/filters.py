from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.forms import SlugField, MultiWidget, Select
from django.http import QueryDict
from django_filters import FilterSet, CharFilter, Filter, ChoiceFilter
from django.utils.translation import ugettext_lazy as _

from learning.models import CourseOffering, Semester
from learning.settings import CENTER_FOUNDATION_YEAR
from learning.utils import semester_slug_re, \
    get_term_index_academic_year_starts, get_term_by_index, \
    get_current_term_pair, TermTuple
from learning.views.utils import get_user_city_code

validate_semester_slug = RegexValidator(
    semester_slug_re,
    _("Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens."),
    'invalid'
)


def validate_semester_year(slug):
    match = semester_slug_re.search(slug)
    if not match or int(match.group("term_year")) < CENTER_FOUNDATION_YEAR:
        raise ValidationError("")

CITIES = [
    ('spb', _("Saint Petersburg")),
    ('nsk', _("Novosibirsk"))
]


class SemesterSlugField(SlugField):
    def __init__(self, *args, **kwargs):
        validators = kwargs.pop("validators", [])
        validators.append(validate_semester_slug)
        validators.append(validate_semester_year)
        kwargs["validators"] = validators
        # TODO: validate year > FOUNDATION_YEAR
        super().__init__(*args, **kwargs)


class SemesterSlugFilter(Filter):
    field_class = SemesterSlugField


class CourseFilter(FilterSet):
    city = ChoiceFilter(name="city_id", empty_label=None, choices=CITIES)
    semester = SemesterSlugFilter(method='semester_slug_filter')

    class Meta:
        model = CourseOffering
        fields = ['city', 'semester']

    def __init__(self, data=None, queryset=None, request=None, **kwargs):
        if data is not None:
            data = data.copy()  # get a mutable copy of the QueryDict
        else:
            data = QueryDict(mutable=True)
        # Provide initial city based on user settings
        city_code = data.pop("city", None)
        if not city_code and get_user_city_code(request):
            user_city = get_user_city_code(request)
            if user_city in settings.CENTER_BRANCHES_CITY_CODES:
                city_code = [user_city]
        # Fallback to spb
        if not city_code:
            city_code = [settings.DEFAULT_CITY_CODE]
        data.setlist("city", city_code)
        super().__init__(data=data, queryset=queryset, request=request, **kwargs)

    def semester_slug_filter(self, queryset, name, value):
        """Queryset will be empty if semester slug is invalid."""
        # TODO: Эта ситуация может возникнуть, только если неправильно кинуть линк. Хитить базу в этом случае или ломать поведение?
        return queryset

    def get_term(self) -> Optional[TermTuple]:
        match = semester_slug_re.search(self.data.get("semester", ""))
        if not match:
            # By default, return academic year and term type for latest
            # available CO.
            print(self.qs)
            if self.qs:
                term = self.qs[0].semester
                term_year = term.year
                term_type = term.type
            else:
                return None
        else:
            term_year = int(match.group("term_year"))
            term_type = match.group("term_type")
        idx = get_term_index_academic_year_starts(term_year, term_type)
        academic_year, _ = get_term_by_index(idx)
        return TermTuple(academic_year, term_type)
