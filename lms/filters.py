from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import SlugField
from django.http import QueryDict
from django_filters import FilterSet, ChoiceFilter, Filter

from core.models import Branch
from courses.constants import SemesterTypes
from courses.models import Course
from courses.utils import semester_slug_re, get_term_index
from learning.settings import Branches


def validate_semester_slug(value):
    match = semester_slug_re.search(value)
    if not match:
        raise ValidationError("Semester slug should be YEAR-TERM_TYPE format")
    term_year = int(match.group("term_year"))
    if term_year < settings.CENTER_FOUNDATION_YEAR:
        raise ValidationError("Wrong semester year")
    term_type = match.group("term_type")
    # More strict rules for term types
    if term_type not in [SemesterTypes.AUTUMN, SemesterTypes.SPRING]:
        raise ValidationError("Supported semester types: [autumn, spring]")
    term_index = get_term_index(term_year, term_type)
    first_term_index = get_term_index(settings.CENTER_FOUNDATION_YEAR,
                                      SemesterTypes.AUTUMN)
    if term_index < first_term_index:
        raise ValidationError("CS Center has no offerings for this period")


class BranchChoiceFilter(ChoiceFilter):
    def filter(self, qs, value):
        """
        Returns union of offline courses and all correspondence courses
        since they are also available in queried city.
        """
        if value == self.null_value:
            value = None
        branch = Branch.objects.get(code=value, site_id=settings.SITE_ID)
        qs = qs.available_in(branch=branch.pk)
        return qs


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
    branch = BranchChoiceFilter(field_name="branch__code", empty_label=None,
                                choices=Branches.choices)
    semester = SemesterSlugFilter(method='semester_slug_filter')

    class Meta:
        model = Course
        fields = ['branch', 'semester']

    def __init__(self, data=None, queryset=None, request=None, **kwargs):
        """
        Resolves `branch` value in the next order:
            * query value
            * valid branch code from user settings
            * default branch code
        """
        if data is not None:
            data = data.copy()  # get a mutable copy of the QueryDict
        else:
            data = QueryDict(mutable=True)
        branch_code = data.pop("branch", None)
        if not branch_code and hasattr(request.user, "branch"):
            branch_code = [request.user.branch.code]
        # For unauthenticated users or users without valid branch code
        if not branch_code:
            branch_code = [settings.DEFAULT_BRANCH_CODE]
        data.setlist("branch", branch_code)
        super().__init__(data=data, queryset=queryset, request=request, **kwargs)

    def semester_slug_filter(self, queryset, name, value):
        return queryset
