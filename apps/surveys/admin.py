from django.contrib import admin
from django.db.models import Count
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from core.admin import meta
from core.filters import AdminRelatedDropdownFilter
from core.timezone.fields import TimezoneAwareDateTimeField
from core.timezone.forms import (
    TimezoneAwareAdminForm, TimezoneAwareAdminSplitDateTimeWidget,
    TimezoneAwareSplitDateTimeField
)
from core.urls import reverse
from core.utils import admin_datetime
from surveys.constants import STATUS_PUBLISHED
from surveys.models import CourseSurvey, Field, FieldChoice, Form
from surveys.services import create_survey_notifications


class FormFieldAdmin(admin.StackedInline):
    model = Field
    exclude = ("description",)
    extra = 0
    classes = ['collapse']
    show_change_link = True


class FormAdmin(admin.ModelAdmin):
    list_display = ("title", "status")
    list_filter = ("status",)
    search_fields = ("title",)
    radio_fields = {"status": admin.HORIZONTAL}
    inlines = [FormFieldAdmin]
    prepopulated_fields = {
        "slug": ("title",)
    }

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if "status" in form.changed_data:
            status = form.cleaned_data["status"]
            if status == STATUS_PUBLISHED:
                try:
                    create_survey_notifications(obj.survey)
                except CourseSurvey.DoesNotExist:
                    pass


class CourseSurveyAdmin(admin.ModelAdmin):
    form = TimezoneAwareAdminForm
    formfield_overrides = {
        TimezoneAwareDateTimeField: {
            'widget': TimezoneAwareAdminSplitDateTimeWidget,
            'form_class': TimezoneAwareSplitDateTimeField
        }
    }
    list_display = ("course", "type", "get_form_status", "get_form_actions",
                    "get_survey_actions", "expire_at_local")
    list_filter = (
        'course__main_branch',
        ('course__semester', AdminRelatedDropdownFilter),
    )
    raw_id_fields = ["course", "email_template"]
    exclude = ("form",)

    @meta(short_description=_("Expires on"))
    def expire_at_local(self, obj):
        return admin_datetime(obj.expire_at_local())

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['course', 'type']
        return []

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if obj is None:
            fields = [f for f in fields if f != "email_template"]
        return fields

    @meta(short_description=_("Status"))
    def get_form_status(self, obj):
        return obj.form.get_status_display()

    @meta(short_description=_("Form"))
    def get_form_actions(self, obj):
        edit_url = reverse("admin:surveys_form_change", args=[obj.form_id])
        preview_url = self.get_view_on_site_url(obj)
        edit_link = f"<a href='{edit_url}'>Редактировать</a>"
        preview_link = f"<a target='_blank' href='{preview_url}'>Смотреть на сайте</a>"
        return mark_safe(f"{preview_link} | {edit_link}")

    def get_survey_actions(self, obj):
        csv_url = reverse("staff:exports_report_survey_submissions",
                          args=[obj.pk, "csv"])
        csv_link = f"<a target='_blank' href='{csv_url}'>CSV</a>"
        txt_url = reverse("staff:exports_report_survey_submissions_stats",
                          args=[obj.pk])
        txt_link = f"<a target='_blank' href='{txt_url}'>TXT</a>"
        return mark_safe(f"{csv_link} | {txt_link}")
    get_survey_actions.short_description = _("Export")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return (qs.select_related("course",
                                  "course__main_branch",
                                  "course__semester",
                                  "course__meta_course",
                                  "form"))

    def get_deleted_objects(self, objs, request):
        objs_ = [o.form for o in objs]
        return super().get_deleted_objects(objs_, request)


class FieldChoiceAdminInline(admin.TabularInline):
    model = FieldChoice
    extra = 0


class FieldAdmin(admin.ModelAdmin):
    list_display = ["label", "field_type", "form", "order"]
    list_filter = ("form__status",)
    search_fields = ("form__title", "label")
    raw_id_fields = ("form",)
    inlines = [FieldChoiceAdminInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return (qs.select_related("form")
                .annotate(total_choices=Count("choices")))


class FieldChoiceAdmin(admin.ModelAdmin):
    list_display = ["label", "field"]
    raw_id_fields = ("field",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("field")


class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ["id", "__str__"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("form")


class FieldEntryAdmin(admin.ModelAdmin):
    list_display = ["field_id", "value"]


admin.site.register(Form, FormAdmin)
admin.site.register(CourseSurvey, CourseSurveyAdmin)
admin.site.register(Field, FieldAdmin)
# admin.site.register(FieldChoice, FieldChoiceAdmin)
# admin.site.register(FormSubmission, FormSubmissionAdmin)
# admin.site.register(FieldEntry, FieldEntryAdmin)
