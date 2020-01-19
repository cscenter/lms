from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import SlugField, forms
from django.http import QueryDict
from django_filters import FilterSet, ChoiceFilter, Filter

from core.models import Branch
from courses.constants import SemesterTypes
from courses.models import Course
from courses.utils import semester_slug_re, get_term_index


class BranchCodeFilter(ChoiceFilter):
    def filter(self, qs, value):
        """
        Filters courses offered internally in a target branch and courses
        available for a long-distance learning in that branch.
        (don't confuse with a distant branch)
        """
        if value == self.null_value:
            value = None
        branch = next(b for b in self.parent.branches if b.code == value)
        term_index = get_term_index(branch.established, SemesterTypes.AUTUMN)
        qs = (qs
              .available_in(branch=branch.pk)
              .filter(semester__index__gte=term_index))
        return qs


class SlugFilter(Filter):
    field_class = SlugField


class SemesterFilter(SlugFilter):
    def filter(self, qs, value):
        return qs


class CoursesFilterForm(forms.Form):
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('semester') and cleaned_data.get('branch'):
            branch_code = cleaned_data['branch']
            branch = next(b for b in self.filter_set.branches
                          if b.code == branch_code)
            semester_value = cleaned_data['semester']
            match = semester_slug_re.search(semester_value)
            if not match:
                msg = "Incorrect term slug format"
                raise ValidationError(msg)
            term_year = int(match.group("term_year"))
            if term_year < branch.established:
                raise ValidationError("Invalid term year")
            term_type = match.group("term_type")
            # More strict rules for term types
            if term_type not in [SemesterTypes.AUTUMN, SemesterTypes.SPRING]:
                raise ValidationError("Supported term types: [autumn, spring]")
            term_index = get_term_index(term_year, term_type)
            first_term_index = get_term_index(branch.established,
                                              SemesterTypes.AUTUMN)
            if term_index < first_term_index:
                raise ValidationError("Invalid term slug")
        return cleaned_data


class CoursesFilter(FilterSet):
    """
    Returns courses available in target branch.
    """
    branch = BranchCodeFilter(field_name="branch__code", empty_label=None,
                              choices=Branch.objects.none())
    # FIXME: мб сначала валидировать request данные? зачем смешивать с фильтрацией? Тогда отсюда можно удалить semester, т.к. он не к месту
    semester = SemesterFilter()

    class Meta:
        model = Course
        form = CoursesFilterForm
        fields = ('branch', 'semester')

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
        self.branches = Branch.objects.for_site(request.site.pk)
        branch_code = data.pop("branch", None)
        if not branch_code and hasattr(request.user, "branch_id"):
            branch = next((b for b in self.branches
                           if b.id == request.user.branch_id), None)
            branch_code = [branch.code] if branch else None
        if not branch_code:
            # TODO: Provide default branch for the site
            branch_code = [settings.DEFAULT_BRANCH_CODE]
        data.setlist("branch", branch_code)
        super().__init__(data=data, queryset=queryset, request=request, **kwargs)
        # Branch code choices depend on current site
        self.form['branch'].field.choices = [(b.code, b.name) for b
                                             in self.branches]

    @property
    def form(self):
        """Attach reference to the filter set"""
        if not hasattr(self, '_form'):
            Form = self.get_form_class()
            if self.is_bound:
                self._form = Form(self.data, prefix=self.form_prefix)
            else:
                self._form = Form(branches=self.branches,
                                  prefix=self.form_prefix)
            self._form.filter_set = self
        return self._form
