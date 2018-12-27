from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from core.exceptions import Redirect
from core.utils import is_club_site
from courses.models import Course


class CourseEnrollmentForm(forms.Form):
    reason = forms.CharField(
        label=_("Почему вы выбрали этот курс?"),
        widget=forms.Textarea(),
        required=False)

    def __init__(self, request, course: Course, **kwargs):
        self.course = course
        self.request = request
        self._custom_errors = None
        super().__init__(**kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit('enroll', 'Записаться на курс'))

    def is_available(self):
        from learning.views.utils import get_student_city_code
        if self._custom_errors is not None:
            return not self._custom_errors
        self._custom_errors = []
        if not self.course.enrollment_is_open:
            # FIXME: replace validation error with exceptions
            error = ValidationError("Course enrollment should be active",
                                    code="deadline")
            self._custom_errors.append(error)
        if is_club_site() and not self.course.is_open:
            error = ValidationError("Club students can't enroll on center "
                                    "courses", code="permissions")
            self._custom_errors.append(error)
        city_code = get_student_city_code(self.request)
        if (not self.course.is_correspondence
                and city_code != self.course.get_city()):
            error = ValidationError("Students can enroll in on courses only "
                                    "from their city", code="permissions")
            self._custom_errors.append(error)
        # Reject if capacity limited and no places available
        # XXX: Race condition. Should be placed in save method
        if self.course.is_capacity_limited:
            if not self.course.places_left:
                msg = _("No places available, sorry")
                messages.error(self.request, msg, extra_tags='timeout')
                raise Redirect(to=self.course.get_absolute_url())
        return not self._custom_errors
