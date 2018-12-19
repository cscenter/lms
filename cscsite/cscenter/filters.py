from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import SlugField
from django.http import QueryDict
from django_filters import FilterSet, Filter, ChoiceFilter
from django.utils.translation import ugettext_lazy as _

from courses.models import Course, Semester
from learning.settings import CENTER_FOUNDATION_YEAR
from courses.settings import SemesterTypes
from courses.utils import get_term_index, semester_slug_re
from learning.views.utils import get_user_city_code


def validate_semester_slug(value):
    match = semester_slug_re.search(value)
    if not match:
        raise ValidationError("Semester slug should be YEAR-TERM_TYPE format")
    term_year = int(match.group("term_year"))
    if term_year < CENTER_FOUNDATION_YEAR:
        raise ValidationError("Wrong semester year")
    term_type = match.group("term_type")
    # More strict rules for term types
    if term_type not in [SemesterTypes.AUTUMN, SemesterTypes.SPRING]:
        raise ValidationError("Supported semester types: [autumn, spring]")
    term_index = get_term_index(term_year, term_type)
    first_term_index = get_term_index(CENTER_FOUNDATION_YEAR,
                                      SemesterTypes.AUTUMN)
    if term_index < first_term_index:
        raise ValidationError("CS Center has no offerings for this period")


CITIES = [
    ('spb', _("Saint Petersburg")),
    ('nsk', _("Novosibirsk"))
]


class CityChoiceFilter(ChoiceFilter):
    def filter(self, qs, value):
        """
        Returns union of offline courses and all correspondence courses
        since they are also available in queried city.
        """
        if value == self.null_value:
            value = None
        qs = qs.in_city(value)
        return qs.distinct() if self.distinct else qs


class SemesterSlugField(SlugField):
    def __init__(self, *args, **kwargs):
        validators = kwargs.pop("validators", [])
        validators.append(validate_semester_slug)
        kwargs["validators"] = validators
        super().__init__(*args, **kwargs)


class SemesterSlugFilter(Filter):
    field_class = SemesterSlugField


class CoursesFilter(FilterSet):
    """
    FilterSet used on /courses/ page.

    Note: `semester` query value is only validated. This field used in
    filtering on client side only.
    """
    city = CityChoiceFilter(field_name="city_id", empty_label=None,
                            choices=CITIES)
    semester = SemesterSlugFilter(method='semester_slug_filter')

    class Meta:
        model = Course
        fields = ['city', 'semester']

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
