from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import SlugField
from django.http import QueryDict
from django_filters import FilterSet, CharFilter, Filter, ChoiceFilter, \
    STRICTNESS
from django.utils.translation import ugettext_lazy as _

from learning.models import CourseOffering, Semester
from learning.settings import CENTER_FOUNDATION_YEAR
from learning.utils import semester_slug_re, \
    get_term_index_academic_year_starts, get_term_by_index, TermTuple, \
    get_term_index
from learning.views.utils import get_user_city_code


def validate_semester_slug(value):
    match = semester_slug_re.search(value)
    if not match:
        raise ValidationError("Semester slug should be YEAR-TERM_TYPE format")
    term_year = int(match.group("term_year"))
    term_type = match.group("term_type")
    # More strict rules for term types
    if term_type not in [Semester.TYPES.autumn, Semester.TYPES.spring]:
        raise ValidationError("Supported semester types: [autumn, spring]")
    term_index = get_term_index(term_year, term_type)
    first_term_index = get_term_index(CENTER_FOUNDATION_YEAR,
                                      Semester.TYPES.autumn)
    if term_index < first_term_index:
        raise ValidationError("CS Center has no offerings for this period")


CITIES = [
    ('spb', _("Saint Petersburg")),
    ('nsk', _("Novosibirsk"))
]


class SemesterSlugField(SlugField):
    def __init__(self, *args, **kwargs):
        validators = kwargs.pop("validators", [])
        validators.append(validate_semester_slug)
        kwargs["validators"] = validators
        super().__init__(*args, **kwargs)


class SemesterSlugFilter(Filter):
    field_class = SemesterSlugField


class CourseFilter(FilterSet):
    """
    CourseFilter used on /courses/ page.

    Note, that we only validate `semester` query value. Later it's used in
    filtering on client side.
    """
    city = ChoiceFilter(name="city_id", empty_label=None, choices=CITIES)
    semester = SemesterSlugFilter(method='semester_slug_filter')

    class Meta:
        model = CourseOffering
        fields = ['city', 'semester']
        # Return empty queryset if not all fields are valid
        strict = STRICTNESS.RETURN_NO_RESULTS

    def __init__(self, data=None, queryset=None, request=None, **kwargs):
        """
        Since we always should have some value for `city`, resolve it in
        next order:
            * query value
            * valid city code from user settings
            * default city code (spb)
        """
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
        # Show default for unauthenticated users or users without valid
        # city code in their settings
        if not city_code:
            city_code = [settings.DEFAULT_CITY_CODE]
        data.setlist("city", city_code)
        super().__init__(data=data, queryset=queryset, request=request, **kwargs)

    def semester_slug_filter(self, queryset, name, value):
        return queryset
