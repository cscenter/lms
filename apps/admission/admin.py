from dal_select2.widgets import Select2Multiple
from import_export.admin import ExportMixin, ImportExportMixin
from import_export.formats.base_formats import CSV
from prettyjson import PrettyJSONWidget

from django.contrib import admin
from django.db import models
from django.db.models import TextField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from admission.forms import InterviewStreamChangeForm
from admission.import_export import ExamRecordResource, OnlineTestRecordResource
from admission.models import (
    Acceptance,
    Applicant,
    Campaign,
    CampaignCity,
    Comment,
    Contest,
    Exam,
    Interview,
    InterviewAssignment,
    InterviewFormat,
    InterviewInvitation,
    InterviewSlot,
    InterviewStream,
    ResidenceCity,
    Test,
)
from admission.roles import Roles
from admission.services import EmailQueueService
from core.admin import meta
from core.timezone.fields import TimezoneAwareDateTimeField
from core.timezone.forms import (
    TimezoneAwareAdminForm,
    TimezoneAwareAdminSplitDateTimeWidget,
    TimezoneAwareSplitDateTimeField,
)
from core.utils import admin_datetime
from core.widgets import AdminRichTextAreaWidget
from users.models import User


class CampaignListFilter(admin.SimpleListFilter):
    title = _("Campaign")
    parameter_name = "campaign_id__exact"

    def lookups(self, request, model_admin):
        campaigns = Campaign.objects.select_related("branch").order_by(
            "-year",
            "branch__name",
        )
        return [(c.pk, str(c)) for c in campaigns]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(**{self.parameter_name: self.value()})
        else:
            return queryset


class ApplicantCampaignListFilter(CampaignListFilter):
    parameter_name = "applicant__campaign_id__exact"


class CampaignAdmin(admin.ModelAdmin):
    form = TimezoneAwareAdminForm
    list_display = ["year", "branch", "current"]
    list_filter = ["branch__site", "branch"]
    raw_id_fields = ["template_interview_feedback"]
    formfield_overrides = {
        TimezoneAwareDateTimeField: {
            "widget": TimezoneAwareAdminSplitDateTimeWidget,
            "form_class": TimezoneAwareSplitDateTimeField,
        },
    }


class OnlineTestAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = OnlineTestRecordResource
    list_display = ["get_applicant", "score", "get_campaign", "yandex_contest_id"]
    list_filter = ["applicant__campaign"]
    search_fields = [
        "applicant__yandex_login",
        "applicant__last_name",
        "applicant__first_name",
        "applicant__email",
    ]
    raw_id_fields = ["applicant"]
    formfield_overrides = {models.JSONField: {"widget": PrettyJSONWidget}}

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = ["contest_status_code"]
        if obj and obj.contest_participant_id:
            readonly_fields.append("contest_participant_id")
        return readonly_fields

    @meta(_("Campaign"))
    def get_campaign(self, obj):
        return obj.applicant.campaign

    @meta(_("Applicant"), admin_order_field="applicant__last_name")
    def get_applicant(self, obj):
        return obj.applicant.full_name

    def get_queryset(self, request):
        qs = super(OnlineTestAdmin, self).get_queryset(request)
        return qs.select_related(
            "applicant",
            "applicant__campaign",
            "applicant__campaign__branch",
        )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == "applicant":
            kwargs["queryset"] = Applicant.objects.select_related(
                "campaign", "campaign__branch"
            ).order_by("last_name")
        return super(OnlineTestAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class ExamAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = ExamRecordResource
    raw_id_fields = ("applicant",)
    list_display = ("__str__", "score", "yandex_contest_id", "status")
    search_fields = [
        "applicant__yandex_login",
        "applicant__last_name",
        "applicant__email",
        "applicant__first_name",
        "yandex_contest_id",
        "contest_participant_id",
    ]
    list_filter = ["applicant__campaign"]
    formfield_overrides = {models.JSONField: {"widget": PrettyJSONWidget}}
    formats = (CSV,)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = ["contest_status_code"]
        if obj and obj.contest_participant_id:
            readonly_fields.append("contest_participant_id")
        return readonly_fields

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "applicant", "applicant__campaign", "applicant__campaign__branch"
        )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == "applicant":
            kwargs["queryset"] = Applicant.objects.select_related(
                "campaign", "campaign__branch"
            ).order_by("last_name")
        return super(ExamAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class ApplicantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "yandex_login",
        "last_name",
        "first_name",
        "campaign",
        "created_local",
    )
    list_filter = [CampaignListFilter, "status"]
    search_fields = (
        "yandex_login",
        "yandex_login_q",
        "stepic_id",
        "first_name",
        "last_name",
        "email",
        "phone",
    )
    raw_id_fields = ("user", "university")

    @meta(_("Created"), admin_order_field="created")
    def created_local(self, obj):
        return admin_datetime(obj.created_local())

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == "campaign":
            kwargs["queryset"] = Campaign.objects.select_related("branch")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class InterviewAssignmentAdmin(admin.ModelAdmin):
    list_display = ["name", "campaign"]
    formfield_overrides = {
        TextField: {"widget": AdminRichTextAreaWidget},
    }

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == "campaign":
            kwargs["queryset"] = Campaign.objects.select_related("branch")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ContestAdmin(admin.ModelAdmin):
    list_display = ["contest_id", "campaign", "type"]
    list_filter = ["campaign__branch__site", CampaignListFilter, "type"]
    formfield_overrides = {models.JSONField: {"widget": PrettyJSONWidget}}

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == "campaign":
            kwargs["queryset"] = Campaign.objects.select_related("branch")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class InterviewFormatAdmin(admin.ModelAdmin):
    raw_id_fields = ("confirmation_template", "reminder_template")
    list_display = ["campaign", "format"]
    list_filter = ["campaign"]


class InterviewAssigneeAdminInline(admin.TabularInline):
    # TODO: create intermediate model with validation by interviewer role, then add 'user' field to raw fields
    model = Interview.interviewers.through
    verbose_name = _("Interviewer")
    verbose_name_plural = _("Interviewers")
    extra = 0
    min_num = 0

    def formfield_for_foreignkey(self, db_field, *args, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(
                group__role=Roles.INTERVIEWER
            ).distinct()
        return super().formfield_for_foreignkey(db_field, *args, **kwargs)


class InterviewAdmin(admin.ModelAdmin):
    form = TimezoneAwareAdminForm
    formfield_overrides = {
        TimezoneAwareDateTimeField: {
            "widget": TimezoneAwareAdminSplitDateTimeWidget,
            "form_class": TimezoneAwareSplitDateTimeField,
        }
    }
    list_display = ["get_date_local", "applicant", "status"]
    list_filter = ["status", ApplicantCampaignListFilter]
    readonly_fields = ["secret_code"]
    raw_id_fields = ["applicant"]
    exclude = ["interviewers"]
    inlines = [InterviewAssigneeAdminInline]

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == "applicant":
            kwargs["queryset"] = Applicant.objects.select_related(
                "campaign", "campaign__branch"
            ).order_by("last_name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @meta(_("Date"), admin_order_field="date")
    def get_date_local(self, obj):
        return admin_datetime(obj.date_local())

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if "date" in form.changed_data:
            EmailQueueService.remove_interview_reminder(obj)
            slots = InterviewSlot.objects.filter(interview_id=obj.pk).select_related(
                "stream", "stream__interview_format"
            )
            for slot in slots:
                EmailQueueService.generate_interview_reminder(obj, slot.stream)


class InterviewCommentAdmin(admin.ModelAdmin):
    list_display = ["get_interview", "get_interviewer", "score"]
    search_fields = ["interview__applicant__last_name"]
    list_filter = ["interview__applicant__campaign"]

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == "interview":
            kwargs["queryset"] = Interview.objects.select_related(
                "applicant",
                "applicant__campaign",
                "applicant__campaign__branch",
            )
        return super(InterviewCommentAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )

    def get_queryset(self, request):
        q = super(InterviewCommentAdmin, self).get_queryset(request)
        q = q.select_related("interview__applicant", "interviewer")
        return q

    @meta(_("Interview"), admin_order_field="interview__applicant__last_name")
    def get_interview(self, obj):
        return obj.interview.applicant.full_name

    @meta(_("Interviewer"))
    def get_interviewer(self, obj):
        return obj.interviewer.get_full_name()


class InterviewSlotAdmin(admin.ModelAdmin):
    list_display = (
        "stream_date",
        "start_at",
    )
    search_fields = ("start_at",)
    list_filter = ("stream__date",)
    raw_id_fields = ("interview",)
    list_select_related = ("stream",)

    @meta(_("Date"), admin_order_field="stream__date")
    def stream_date(self, obj):
        return obj.stream.date.strftime("%d.%m.%Y")


class InterviewSlotsInline(admin.TabularInline):
    model = InterviewSlot
    # FIXME: edit queryset for interview and remove from readonly
    readonly_fields = ["interview", "start_at", "end_at"]

    def has_add_permission(self, request, obj=None):
        return False


class InterviewStreamAdmin(admin.ModelAdmin):
    form = InterviewStreamChangeForm
    list_select_related = ("campaign", "campaign__branch")
    list_display = ["date", "start_at", "end_at", "campaign"]
    ordering = ["-date", "-start_at"]
    list_filter = [CampaignListFilter]
    inlines = [InterviewSlotsInline]
    formfield_overrides = {
        models.ManyToManyField: {
            "widget": Select2Multiple(attrs={"data-width": "style"})
        }
    }

    def get_readonly_fields(self, request, obj=None):
        """
        Interviewers choices restricted by interviewer group list. If someone
        was removed from this list, they won't be in rendered widget anymore and
        we can missed information about them on save action. To prevent this,
        set readonly for `interviewers` in edit view if stream is old enough.
        """
        if not obj:
            return []
        readonly_fields = ["start_at", "end_at", "duration"]
        if obj.interview_invitations.exists():
            readonly_fields.append("date")
        if obj.date < timezone.now().date():
            readonly_fields.append("interviewers")
        return readonly_fields


class InterviewStreamsInline(admin.TabularInline):
    model = InterviewInvitation.streams.through

    def has_add_permission(self, request, obj=None):
        return False


class InterviewInvitationAdmin(admin.ModelAdmin):
    model = InterviewInvitation
    list_select_related = [
        "applicant",
        "applicant__campaign__branch",
        "applicant__campaign__branch__site",
    ]
    list_display = ["get_applicant", "get_campaign_branch", "get_accepted"]
    raw_id_fields = ("applicant", "interview")
    readonly_fields = ("secret_code",)
    # Is it possible to restrict streams values by applicant?
    # inlines = [InterviewStreamsInline]

    @meta(_("Accepted"))
    def get_accepted(self, obj):
        return _("Yes") if obj.is_accepted else _("No")

    @meta(_("Applicant"))
    def get_applicant(self, obj):
        return obj.applicant.full_name

    @meta(_("Branch"))
    def get_campaign_branch(self, obj):
        return obj.applicant.campaign.branch


class AcceptanceAdmin(admin.ModelAdmin):
    list_display = ("applicant_name", "get_campaign", "status", "created_at")
    list_filter = ["status", "applicant__campaign"]
    raw_id_fields = ("applicant",)
    list_select_related = ("applicant__campaign__branch",)
    search_fields = ["applicant__last_name"]

    @meta(_("Applicant"))
    def applicant_name(self, obj):
        return obj.applicant.full_name

    @meta(_("Campaign"))
    def get_campaign(self, obj):
        return obj.applicant.campaign

    def get_readonly_fields(self, request, obj=None):
        if obj is None or obj.pk is None:
            return []
        return ["confirmation_code"]


@admin.register(ResidenceCity)
class ResidenceCityAdmin(admin.ModelAdmin):
    list_select_related = ("country",)
    list_display = ("id", "name", "display_name", "country", "order")
    list_filter = ("country",)
    search_fields = ("name", "display_name")


@admin.register(CampaignCity)
class CampaignCityAdmin(admin.ModelAdmin):
    list_select_related = ("campaign__branch__city", "city")
    list_display = ("id", "campaign", "city")
    list_filter = (CampaignListFilter,)
    raw_id_fields = (
        "campaign",
        "city",
    )


admin.site.register(Campaign, CampaignAdmin)
admin.site.register(Applicant, ApplicantAdmin)
admin.site.register(Test, OnlineTestAdmin)
admin.site.register(Exam, ExamAdmin)
admin.site.register(InterviewFormat, InterviewFormatAdmin)
admin.site.register(Interview, InterviewAdmin)
admin.site.register(InterviewAssignment, InterviewAssignmentAdmin)
admin.site.register(Contest, ContestAdmin)
admin.site.register(Comment, InterviewCommentAdmin)
admin.site.register(InterviewStream, InterviewStreamAdmin)
admin.site.register(InterviewSlot, InterviewSlotAdmin)
admin.site.register(InterviewInvitation, InterviewInvitationAdmin)
admin.site.register(Acceptance, AcceptanceAdmin)
