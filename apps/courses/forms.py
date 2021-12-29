import datetime
from collections import defaultdict
from typing import Any, Dict, List, Optional, Type

from crispy_forms.bootstrap import Tab, TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.forms import CANCEL_SAVE_PAIR
from core.models import LATEX_MARKDOWN_HTML_ENABLED
from core.timezone.constants import DATE_FORMAT_RU, TIME_FORMAT_RU
from core.timezone.forms import TimezoneAwareModelForm, TimezoneAwareSplitDateTimeField
from core.utils import bucketize
from core.widgets import DateInputTextWidget, TimeInputTextWidget, UbereditorWidget
from courses.constants import AssigneeMode, AssignmentFormat, ClassTypes
from courses.models import (
    Assignment, Course, CourseClass, CourseNews, LearningSpace, MetaCourse
)
from courses.selectors import get_course_teachers
from courses.services import CourseService
from grading.constants import CheckingSystemTypes
from grading.models import CheckingSystem
from grading.services import CheckerService

__all__ = ('MetaCourseForm', 'CourseUpdateForm', 'CourseNewsForm',
           'CourseClassForm', 'AssignmentForm', 'AssignmentResponsibleTeachersForm',
           'AssignmentResponsibleTeachersFormFactory',
           'StudentGroupAssigneeForm', 'StudentGroupAssigneeFormFactory')

from courses.utils import execution_time_string
from learning.models import StudentGroup, StudentGroupAssignee
from learning.services import StudentGroupService

DROP_ATTACHMENT_LINK = '<a href="{}"><i class="fa fa-trash-o"></i>&nbsp;{}</a>'


class MultipleStudentGroupField(forms.TypedMultipleChoiceField):
    def __init__(self, **kwargs):
        super().__init__(coerce=int, **kwargs)

    def prepare_value(self, value):
        if not value:
            return super().prepare_value(value)
        return [
            # Initial data stores model objects
            (sg.pk if isinstance(sg, StudentGroup) else sg) for sg in value
        ]

    def widget_attrs(self, widget):
        widget_attrs = super().widget_attrs(widget)
        widget_attrs.update({
            'class': 'multiple-select bs-select-hidden',
            'title': _('To all groups'),
        })
        return widget_attrs


class MetaCourseForm(forms.ModelForm):
    name_ru = forms.CharField(
        label=_("Course|name"),
        required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'off',
                                      'autofocus': 'autofocus'}))
    description_ru = forms.CharField(
        label=_("Course|description"),
        required=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        widget=UbereditorWidget)

    @property
    def helper(self):
        helper = FormHelper()
        helper.layout = Layout(
            TabHolder(
                Tab(
                    'RU',
                    'name_ru',
                    'description_ru',
                ),
                Tab(
                    'EN',
                    'name_en',
                    'description_en',
                ),
            ),
            CANCEL_SAVE_PAIR)
        return helper

    class Meta:
        model = MetaCourse
        fields = ('name_ru', 'name_en', 'description_ru', 'description_en')


class CourseUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            TabHolder(
                Tab(
                    'RU',
                    'description_ru',
                ),
                Tab(
                    'EN',
                    'description_en',
                ),
                template='crispy_forms/square_tabs.html'
            ),
            Div('internal_description'),
            Div('contacts'),
            CANCEL_SAVE_PAIR)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Course
        fields = ['description_ru', 'description_en', 'internal_description', 'contacts']
        widgets = {
            'description_ru': UbereditorWidget,
            'description_en': UbereditorWidget,
            'internal_description': UbereditorWidget,
            'contacts': UbereditorWidget
        }


class CourseNewsForm(forms.ModelForm):
    title = forms.CharField(
        label=_("Title"),
        required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'off',
                                      'autofocus': 'autofocus'}))
    text = forms.CharField(
        label=_("Text"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        required=True,
        widget=UbereditorWidget)

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('title', 'text'),
            CANCEL_SAVE_PAIR)
        super().__init__(*args, **kwargs)
        if course:
            self.instance.course = course

    class Meta:
        model = CourseNews
        fields = ['title', 'text']


class CourseClassForm(forms.ModelForm):
    venue = forms.ModelChoiceField(
        queryset=LearningSpace.objects.select_related('location'),
        label=_("Venue"),
        empty_label=None)
    type = forms.ChoiceField(
        label=_("Type"),
        choices=ClassTypes.choices)
    name = forms.CharField(
        label=_("CourseClass|Name"),
        widget=forms.TextInput(attrs={'autocomplete': 'off'}))
    description = forms.CharField(
        label=_("Description"),
        required=False,
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        widget=UbereditorWidget(attrs={'autofocus': 'autofocus'}))
    slides = forms.FileField(
        label=_("Slides"),
        required=False,
        widget=forms.ClearableFileInput)
    attachments = forms.FileField(
        label=_("Attached files"),
        required=False,
        help_text=_("You can select multiple files"),
        widget=forms.ClearableFileInput(attrs={'multiple': 'multiple'}))
    other_materials = forms.CharField(
        label=_("CourseClass|Other materials"),
        required=False,
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        widget=UbereditorWidget)
    date = forms.DateField(
        label=_("Date"),
        help_text=_("Format: dd.mm.yyyy"),
        widget=DateInputTextWidget(attrs={'class': 'datepicker'}))
    # TODO: validate ambiguous time points
    starts_at = forms.TimeField(
        label=_("Starts at"),
        help_text=_("Format: hh:mm"),
        widget=TimeInputTextWidget())
    ends_at = forms.TimeField(
        label=_("Ends at"),
        help_text=_("Format: hh:mm"),
        widget=TimeInputTextWidget())
    time_zone = forms.ChoiceField(
        label=_("Time Zone"),
        required=True,
        help_text="&nbsp;")
    restricted_to = MultipleStudentGroupField(
        label=_("Student Groups"),
        required=False,
        help_text=_("Restrict course class visibility in the student schedule"))

    class Meta:
        model = CourseClass
        fields = ['venue', 'type', 'date', 'starts_at', 'ends_at', 'time_zone', 'name',
                  'description', 'slides', 'attachments', 'video_url',
                  'other_materials', 'materials_visibility', 'restricted_to']

    def __init__(self, locale='en', **kwargs):
        course = kwargs.pop('course', None)
        assert course is not None
        super().__init__(**kwargs)
        self.fields['venue'].queryset = (LearningSpace.objects
                                         .select_related('location')
                                         .filter(branch__in=course.branches.all())
                                         .distinct()
                                         .order_by('name'))
        self.fields['time_zone'].choices = CourseService.get_time_zones(course, locale=locale)
        field_restrict_to = self.fields['restricted_to']
        field_restrict_to.choices = StudentGroupService.get_choices(course)
        self.instance.course = course

    def clean_date(self):
        date = self.cleaned_data['date']
        # Validate this since 'course' could be invalid
        if 'course' in self.cleaned_data:
            course = self.cleaned_data['course']
            semester_start = course.semester.starts_at.date()
            semester_end = course.semester.ends_at.date()
            assert semester_start <= semester_end
            if not semester_start <= date <= semester_end:
                raise ValidationError(
                    _("Inconsistent with this course's "
                      "semester (from %(starts_at)s to %(ends_at)s)"),
                    code='date_out_of_semester',
                    params={'starts_at': semester_start,
                            'ends_at': semester_end})
        return date


class AssignmentDurationField(forms.DurationField):
    """
    Supports `hours:minutes` format instead of Django's '%d %H:%M:%S.%f'.
    """
    default_error_messages = {
        'required': _('Enter the time spent on the assignment.'),
        'invalid': _('Enter a valid duration in a HH:MM format'),
        'overflow': _('The number of days must be less than {max_days}.')
    }

    def prepare_value(self, value):
        if isinstance(value, datetime.timedelta):
            return execution_time_string(value)
        return value

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, datetime.timedelta):
            return value
        try:
            hours, minutes = map(int, str(value).split(":", maxsplit=1))
            value = datetime.timedelta(hours=hours, minutes=minutes)
        except ValueError:
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        except OverflowError:
            raise ValidationError(self.error_messages['overflow'].format(
                max_days=datetime.timedelta.max.days,
            ), code='overflow')
        if value is None:
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        if value.total_seconds() < 0:
            raise ValidationError(self.error_messages['invalid'],
                                  code='invalid')
        # Intentionally don't use this value in overflow validation to be
        # more annoying for those who wants to abuse duration field
        max_days = 3
        if value.days > max_days:
            msg = _("There must be an error in the duration specified. "
                    "Please, contact curators for this problem.")
            raise ValidationError(msg, code='overflow')
        return value


class AssignmentForm(TimezoneAwareModelForm):
    prefix = "assignment"

    title = forms.CharField(
        label=_("Title"),
        widget=forms.TextInput(attrs={'autocomplete': 'off'}))
    text = forms.CharField(
        label=_("Text"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        widget=UbereditorWidget(attrs={'autofocus': 'autofocus'}))
    deadline_at = TimezoneAwareSplitDateTimeField(
        label=_("Deadline"),
        input_date_formats=[DATE_FORMAT_RU],
        input_time_formats=[TIME_FORMAT_RU],
    )
    time_zone = forms.ChoiceField(
        label=_("Time Zone"),
        required=True)
    attachments = forms.FileField(
        label=_("Attached files"),
        required=False,
        help_text=_("You can select multiple files"),
        widget=forms.ClearableFileInput(attrs={'multiple': 'multiple'}))
    passing_score = forms.IntegerField(
        label=_("Passing score"),
        initial=2)
    maximum_score = forms.IntegerField(
        label=_("Maximum score"),
        initial=5)
    weight = forms.DecimalField(
        label=_("Assignment Weight"),
        initial=1,
        min_value=0, max_value=1, max_digits=3, decimal_places=2,
        help_text=_("Assignment contribution to the course total score. "
                    "It takes into account in the gradebook.")
    )
    ttc = AssignmentDurationField(
        label=_("Time to Completion"),
        required=False,
        help_text=_("Estimated amount of time required for the task to be completed"),
        widget=forms.TextInput(
            attrs={"autocomplete": "off",
                   "class": "form-control",
                   "placeholder": _("hours:minutes")}))
    restricted_to = MultipleStudentGroupField(
        label=_("Available for Groups"),
        required=False,
        help_text=_("Restrict assignment to selected groups. Available to all by default."))
    checking_system = forms.ModelChoiceField(
        label=_("Checking System"),
        required=False,
        queryset=CheckingSystem.objects.all()
    )
    checker_url = forms.URLField(
        label=_("Checker URL"),
        required=False,
        help_text=_("For example, URL of the Yandex.Contest problem: "
                    "https://contest.yandex.ru/contest/3/problems/A/")
    )
    assignee_mode = forms.ChoiceField(
        label=_("Selection Mode"),
        choices=AssigneeMode.choices,
        required=True)

    def __init__(self, course: Course, locale: Optional[str] = "en", **kwargs: Any):
        super().__init__(**kwargs)
        self.instance.course = course
        self.fields['ttc'].required = course.ask_ttc
        self.fields['time_zone'].choices = CourseService.get_time_zones(course, locale=locale)
        # Student groups
        field_restrict_to = self.fields['restricted_to']
        field_restrict_to.choices = StudentGroupService.get_choices(course)
        # Checker settings
        checker = self.instance.checker
        if checker:
            self.fields['checking_system'].initial = checker.checking_system
            self.fields['checker_url'].initial = checker.url

    class Meta:
        model = Assignment
        fields = ('title', 'text', 'deadline_at', 'time_zone', 'attachments',
                  'submission_type', 'passing_score', 'maximum_score',
                  'weight', 'ttc', 'restricted_to', 'assignee_mode')

    def clean(self):
        cleaned_data = super().clean()
        submission_type = cleaned_data.get('submission_type')
        if submission_type in AssignmentFormat.with_checker:
            checking_system = cleaned_data.get('checking_system')
            checker_url = cleaned_data.get('checker_url')
            if checking_system:
                if checking_system.type != CheckingSystemTypes.YANDEX:
                    self.add_error('checker_url', "Checking system type is not supported")
                try:
                    CheckerService.resolve_yandex_contest_problem_alias(checker_url)
                except ValueError as e:
                    self.add_error('checker_url', str(e))
            elif checker_url:
                self.add_error('checker_url', _("URL is specified but checking system is empty"))
        return cleaned_data

    def save(self, commit=True):
        submission_type = self.cleaned_data['submission_type']
        if submission_type in AssignmentFormat.with_checker:
            checking_system = self.cleaned_data['checking_system']
            checker = None
            if checking_system:
                checker_url = self.cleaned_data['checker_url']
                checker = CheckerService.get_or_create_checker_from_url(
                    checking_system, checker_url)
            self.instance.checker = checker
        instance = super().save()
        return instance


class AssignmentResponsibleTeachersForm(forms.Form):
    prefix = "responsible"
    field_prefix = "teacher"

    @property
    def helper(self):
        helper = FormHelper()
        helper.disable_csrf = True
        helper.form_tag = False
        return helper

    def clean(self):
        data = self.to_internal()
        if not data.get('responsible_teachers'):
            raise ValidationError("Укажите хотя бы одного преподавателя")
        return self.cleaned_data

    def to_internal(self):
        if not self.is_valid():
            return {}
        data = {'responsible_teachers': []}
        for field_name, field_value in self.cleaned_data.items():
            if field_name.startswith(self.field_prefix):
                pk, name = field_name[len(self.field_prefix) + 1:].split("-", maxsplit=1)
                if name == "active" and field_value:
                    data['responsible_teachers'].append(int(pk))
        return data


class AssignmentResponsibleTeachersFormFactory:
    field_prefix = AssignmentResponsibleTeachersForm.field_prefix

    @classmethod
    def build_form_class(cls, course: Course):
        cls_dict = {}
        # TODO: cache the result of get_course_teachers
        for course_teacher in get_course_teachers(course=course):
            key = f"{cls.field_prefix}-{course_teacher.pk}-active"
            teacher_name = course_teacher.teacher.get_full_name(last_name_first=True)
            cls_dict[key] = forms.BooleanField(label=teacher_name, required=False)
        return type("AssignmentResponsibleTeachersForm", (AssignmentResponsibleTeachersForm,), cls_dict)

    @classmethod
    def to_initial_state(cls, course: Course, assignment: Optional[Assignment] = None):
        initial = {}
        if assignment is None:
            course_teachers = list(get_course_teachers(course=course))
            selected = [ct for ct in course_teachers if ct.roles.reviewer]
        else:
            selected = assignment.assignees.all()
        for course_teacher in selected:
            initial[f"{cls.field_prefix}-{course_teacher.pk}-active"] = True
        return initial

    @classmethod
    def build_form(cls, course: Course, *, assignment: Optional[Assignment] = None,
                   **form_kwargs: Any) -> AssignmentResponsibleTeachersForm:
        form_class = cls.build_form_class(course)
        form_kwargs.setdefault("initial", cls.to_initial_state(course, assignment))
        return form_class(**form_kwargs)


class StudentGroupAssigneeForm(forms.Form):
    prefix = "student-group"
    field_prefix = "assignee"

    @property
    def helper(self):
        helper = FormHelper()
        helper.disable_csrf = True
        helper.form_tag = False
        return helper

    def to_internal(self) -> Dict[int, List[int]]:
        if not self.is_valid():
            return {}
        data = defaultdict(list)
        for field_name, field_value in self.cleaned_data.items():
            if field_name.startswith(self.field_prefix):
                pk, name = field_name[len(self.field_prefix) + 1:].split("-", maxsplit=1)
                if name == "teacher":
                    data[int(pk)].append(int(field_value))
        return data


class StudentGroupAssigneeFormFactory:
    field_prefix = StudentGroupAssigneeForm.field_prefix

    @classmethod
    def build_form_class(cls, course: Course, is_required: Optional[bool] = False):
        student_groups = CourseService.get_student_groups(course)
        course_teachers = get_course_teachers(course=course)
        cls_dict = {'student_groups': student_groups}
        choices = [
            ('', '-------'),
            *((ct.pk, ct.teacher.get_full_name(last_name_first=True))
              for ct in course_teachers)
        ]
        for student_group in student_groups:
            prefix = f"{cls.field_prefix}-{student_group.pk}"
            cls_dict[f"{prefix}-name"] = forms.CharField(label=_("Name"), max_length=255,
                                                         initial=student_group.name,
                                                         disabled=True)
            cls_dict[f"{prefix}-teacher"] = forms.ChoiceField(label=_("Teacher"),
                                                              choices=choices,
                                                              required=is_required)
        return type("StudentGroupAssigneeForm", (StudentGroupAssigneeForm,), cls_dict)

    @classmethod
    def get_initial_state(cls, course: Course,
                          assignment: Optional[Assignment] = None) -> Dict[str, int]:
        if assignment and assignment.course_id != course.pk:
            raise ValidationError(f"Assignment {assignment} is not from the course {course}")
        initial = {}
        if assignment is not None and assignment.assignee_mode == AssigneeMode.STUDENT_GROUP_CUSTOM:
            assigned_teachers = (StudentGroupAssignee.objects
                                 .filter(assignment=assignment))
            grouped = bucketize(assigned_teachers, key=lambda sga: sga.student_group_id)
            for sg_id, responsible_teachers in grouped.items():
                if len(responsible_teachers) == 1:
                    value = responsible_teachers[0].assignee_id
                    initial[f"{cls.field_prefix}-{sg_id}-teacher"] = value
        return initial

    @classmethod
    def build_form(cls, course: Course, *, is_required: Optional[bool] = True,
                   assignment: Optional[Assignment] = None, **form_kwargs: Any) -> StudentGroupAssigneeForm:
        form_class = cls.build_form_class(course, is_required)
        form_kwargs.setdefault("initial", cls.get_initial_state(course, assignment))
        return form_class(**form_kwargs)
