from django.contrib import admin
from django.db.models import Count
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from core.filters import AdminRelatedDropdownFilter
from core.urls import reverse
from surveys.constants import STATUS_PUBLISHED
from surveys.models import Form, Field, FieldChoice, CourseSurvey


class FormFieldAdmin(admin.StackedInline):
    model = Field
    exclude = ("description",)
    extra = 0
    classes = ['collapse']


class FormAdmin(admin.ModelAdmin):
    list_display = ("title", "status")
    list_filter = ("status",)
    search_fields = ("title",)
    radio_fields = {"status": admin.HORIZONTAL}
    inlines = [FormFieldAdmin]
    prepopulated_fields = {
        "slug": ("title",)
    }

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = []
        if obj and obj.status == STATUS_PUBLISHED:
            readonly_fields.append("status")
        return readonly_fields


class CourseSurveyAdmin(admin.ModelAdmin):
    list_display = ("course", "get_city", "type",
                    "get_form_actions", "get_survey_actions",
                    "publish_at", "expire_at")
    list_filter = (
        'course__city',
        ('course__semester', AdminRelatedDropdownFilter),
    )
    raw_id_fields = ["course", "email_template"]
    exclude = ("form",)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['course', 'type']
        return []

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if obj is None:
            fields = [f for f in fields if f != "email_template"]
        return fields

    def get_form_actions(self, obj):
        form_url = reverse("admin:surveys_form_change", args=[obj.form_id])
        url = f"<a href='{form_url}'>Редактировать форму</a>"
        return mark_safe(f"{obj.form.get_status_display()} | {url}")
    get_form_actions.short_description = _("Status")

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
                                  "course__city",
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
