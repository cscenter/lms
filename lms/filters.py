import re

from django_filters import ChoiceFilter, Filter, FilterSet

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import SlugField, forms
from django.http import QueryDict

from core.models import Branch
from courses.constants import SemesterTypes
from courses.models import Course
from courses.utils import get_current_term_pair, get_term_index
from users.constants import student_permission_roles
from users.models import StudentProfile
from users.services import get_student_profiles


class BranchCodeFilter(ChoiceFilter):
    def filter(self, qs, value):
        """
        Filters courses offered internally in a target branch and courses
        available for a long-distance learning in that branch.
        (don't confuse with a distant branch)
        """
        if value == self.null_value:
            value = None
        branch = next(b for b in self.parent.site_branches if b.code == value)
        term_index = get_term_index(branch.established, SemesterTypes.AUTUMN)
        qs = (qs
              .available_in(branch.pk)
              .filter(semester__index__gte=term_index))
        return qs


class SlugFilter(Filter):
    field_class = SlugField


class SemesterFilter(SlugFilter):
    def filter(self, qs, value):
        return qs


_term_types = r"|".join(slug for slug, _ in SemesterTypes.choices)
semester_slug_re = re.compile(r"^(?P<term_year>\d{4})-(?P<term_type>" + _term_types + r")$")


class CoursesFilterForm(forms.Form):
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('semester') and cleaned_data.get('branch'):
            branch_code = cleaned_data['branch']
            branch = next(b for b in self.filter_set.site_branches
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
    Returns courses available in a target branch.
    """
    branch = BranchCodeFilter(empty_label=None, choices=Branch.objects.none())
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
        self.site_branches = self.get_branches(request)
        branch_code = data.pop("branch", None)
        if request.user.roles.issubset(student_permission_roles):
            profiles = get_student_profiles(user=request.user,
                                            site=request.site,
                                            fetch_graduate_profile=True,
                                            fetch_status_history=True)
            user_branch_ids = [profile.branch_id for profile in profiles]
            self.user_branches = Branch.objects.filter(
                active=True,
                id__in=user_branch_ids,
                site_id=request.site.pk
            )
            main_branch_code = profiles[0].branch.code
            if not branch_code and main_branch_code:
                branch_code = [main_branch_code]
        else:
            self.user_branches = self.site_branches
            if not branch_code and hasattr(request.user, "branch_id"):
                branch = next((b for b in self.site_branches
                               if b.id == request.user.branch_id), None)
                branch_code = [branch.code] if branch else None
        if not branch_code:
            # TODO: Provide default branch for the site
            branch_code = [settings.DEFAULT_BRANCH_CODE]
        data.setlist("branch", branch_code)
        super().__init__(data=data, queryset=queryset, request=request, **kwargs)
        # Branch code choices depend on current site
        current_term = get_current_term_pair()
        self.form['branch'].field.choices = [(b.code, b.name) for b in self.user_branches
                                             if b.established <= current_term.academic_year]

    def get_branches(self, request):
        return Branch.objects.for_site(request.site.pk)

    @property
    def form(self):
        """Attach reference to the filter set"""
        if not hasattr(self, '_form'):
            Form = self.get_form_class()
            if self.is_bound:
                self._form = Form(self.data, prefix=self.form_prefix)
            else:
                self._form = Form(branches=self.site_branches,
                                  prefix=self.form_prefix)
            self._form.filter_set = self
        return self._form
