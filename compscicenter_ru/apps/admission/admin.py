from django.db import models
from django.db.models import TextField
from django.utils import timezone
from import_export.formats.base_formats import CSV
from jsonfield import JSONField
from prettyjson import PrettyJSONWidget
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from import_export.admin import ExportMixin, ImportMixin, ImportExportMixin

from core.admin import CityAwareModelForm, CityAwareAdminSplitDateTimeWidget, \
    CityAwareSplitDateTimeField, meta
from core.widgets import AdminRichTextAreaWidget
from core.utils import admin_datetime
from admission.forms import InterviewStreamChangeForm
from admission.import_export import OnlineTestRecordResource, \
    ExamRecordResource
from admission.models import Campaign, Interview, Applicant, Test, \
    Exam, Comment, InterviewAssignment, Contest, InterviewSlot, InterviewStream, \
    InterviewInvitation


class CampaignListFilter(admin.SimpleListFilter):
    title = _('Campaign')
    parameter_name = 'campaign_id__exact'

    def lookups(self, request, model_admin):
        campaigns = (Campaign.objects
                     .select_related("branch")
                     .order_by("-branch_id", "-year"))
        return [(c.pk, str(c)) for c in campaigns]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(**{self.parameter_name: self.value()})
        else:
            return queryset


class CampaignAdmin(admin.ModelAdmin):
    form = CityAwareModelForm
    list_display = ['year', 'branch', 'current']
    list_filter = ['branch']
    formfield_overrides = {
        models.DateTimeField: {
            'widget': CityAwareAdminSplitDateTimeWidget,
            'form_class': CityAwareSplitDateTimeField
        },
    }


class OnlineTestAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = OnlineTestRecordResource
    list_display = ['__str__', 'score', 'get_campaign', 'yandex_contest_id']
    list_filter = ['applicant__campaign']
    search_fields = ['applicant__yandex_id', 'applicant__surname',
                     'applicant__first_name', 'applicant__email']
    raw_id_fields = ['applicant']
    formfield_overrides = {
        JSONField: {'widget': PrettyJSONWidget}
    }

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = ["contest_status_code"]
        if obj and obj.contest_participant_id:
            readonly_fields.append("contest_participant_id")
        return readonly_fields

    def get_campaign(self, obj):
        return obj.applicant.campaign
    get_campaign.short_description = _("Campaign")

    def get_queryset(self, request):
        qs = super(OnlineTestAdmin, self).get_queryset(request)
        return qs.select_related('applicant',
                                 'applicant__campaign',
                                 'applicant__campaign__city',
                                 'applicant__campaign__branch',)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'applicant':
            kwargs['queryset'] = (
                Applicant.objects
                         .select_related("campaign", "campaign__city",
                                         "campaign__branch")
                         .order_by("surname"))
        return (super(OnlineTestAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))


class ExamAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = ExamRecordResource
    raw_id_fields = ("applicant",)
    list_display = ('__str__', 'score', 'yandex_contest_id', 'status')
    search_fields = ['applicant__yandex_id', 'applicant__surname',
                     'applicant__first_name', 'yandex_contest_id']
    list_filter = ['applicant__campaign']
    formfield_overrides = {
        JSONField: {'widget': PrettyJSONWidget}
    }
    formats = (CSV,)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = ["contest_status_code"]
        if obj and obj.contest_participant_id:
            readonly_fields.append("contest_participant_id")
        return readonly_fields

    def get_queryset(self, request):
        qs = super(ExamAdmin, self).get_queryset(request)
        return qs.select_related('applicant',
                                 'applicant__campaign',
                                 'applicant__campaign__city')

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'applicant':
            kwargs['queryset'] = (
                Applicant.objects
                         .select_related("campaign", "campaign__city")
                         .order_by("surname"))
        return (super(ExamAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))


class ApplicantAdmin(admin.ModelAdmin):
    list_display = ('id', 'yandex_id', 'surname', 'first_name', 'campaign',
                    'created_local')
    list_filter = [CampaignListFilter, 'status']
    search_fields = ('yandex_id', 'yandex_id_normalize', 'stepic_id',
                     'first_name', 'surname', 'email', 'phone')
    readonly_fields = ['yandex_id_normalize']

    def created_local(self, obj):
        return admin_datetime(obj.created_local())
    created_local.admin_order_field = 'created'
    created_local.short_description = _("Created")

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'campaign':
            kwargs['queryset'] = (Campaign.objects.select_related("city"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class InterviewAssignmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'campaign']
    formfield_overrides = {
        TextField: {'widget': AdminRichTextAreaWidget},
    }

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'campaign':
            kwargs['queryset'] = (Campaign.objects.select_related("city"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ContestAdmin(admin.ModelAdmin):
    list_display = ['contest_id', 'campaign', 'type']
    list_filter = [CampaignListFilter, 'type']
    formfield_overrides = {
        JSONField: {'widget': PrettyJSONWidget}
    }

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'campaign':
            kwargs['queryset'] = (Campaign.objects.select_related("city"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class InterviewAdmin(admin.ModelAdmin):
    form = CityAwareModelForm
    formfield_overrides = {
        models.DateTimeField: {
            'widget': CityAwareAdminSplitDateTimeWidget,
            'form_class': CityAwareSplitDateTimeField
        }
    }
    list_display = ['get_date_local', 'applicant', 'status']
    list_filter = ['status', 'applicant__campaign']
    raw_id_fields = ["applicant"]

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'applicant':
            kwargs['queryset'] = (
                Applicant.objects
                         .select_related("campaign", "campaign__city")
                         .order_by("surname"))
        return (super(InterviewAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))

    def get_date_local(self, obj):
        return admin_datetime(obj.date_local())
    get_date_local.admin_order_field = 'date'
    get_date_local.short_description = _("Date")


class InterviewCommentAdmin(admin.ModelAdmin):
    list_display = ['get_interview', 'get_interviewer', 'score']
    search_fields = ['interview__applicant__surname']
    list_filter = ['interview__applicant__campaign']

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'interview':
            kwargs['queryset'] = (
                Interview.objects.select_related("applicant",
                                                 "applicant__campaign",
                                                 "applicant__campaign__city",))
        return (super(InterviewCommentAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))

    def get_queryset(self, request):
        q = super(InterviewCommentAdmin, self).get_queryset(request)
        q = q.select_related("interview__applicant",
                             "interviewer")
        return q

    @meta(_("Interview"), admin_order_field="interview__applicant__surname")
    def get_interview(self, obj):
        return obj.interview.applicant.get_full_name()

    @meta(_("Interviewer"))
    def get_interviewer(self, obj):
        return obj.interviewer.get_full_name()


class InterviewSlotAdmin(admin.ModelAdmin):
    search_fields = ['stream__date']
    raw_id_fields = ("interview",)


class InterviewSlotsInline(admin.TabularInline):
    model = InterviewSlot
    # FIXME: edit queryset for interview and remove from readonly
    readonly_fields = ["interview", "start_at", "end_at"]

    def has_add_permission(self, request, obj=None):
        return False


# TODO: Как проверять, что потоки не пересекаются? Если совпадает место?
class InterviewStreamAdmin(admin.ModelAdmin):
    form = InterviewStreamChangeForm
    list_select_related = ['campaign', 'campaign__city']
    list_display = ["date", "campaign"]
    list_filter = [CampaignListFilter]
    inlines = [InterviewSlotsInline]
    # TODO: how to customize time widget format to H:M?

    def get_readonly_fields(self, request, obj=None):
        """
        Interviewers choices restricted by interviewer group list. If someone
        was removed from this list, they won't be in rendered widget anymore and
        we can missed information about them on save action. To prevent this,
        set readonly for `interviewers` in edit view if stream is old enough.
        """
        if not obj:
            return []
        elif obj.date < timezone.now().date():
            return ['start_at', 'end_at', 'duration', 'interviewers', 'date']
        else:
            return ['start_at', 'end_at', 'duration', 'date']


class InterviewStreamsInline(admin.TabularInline):
    model = InterviewInvitation.streams.through

    def has_add_permission(self, request, obj=None):
        return False


class InterviewInvitationAdmin(admin.ModelAdmin):
    model = InterviewInvitation
    list_select_related = ["applicant", "applicant__campaign__city"]
    list_display = ['get_applicant', 'get_campaign_city', 'get_accepted']
    raw_id_fields = ("applicant", "interview")
    readonly_fields = ("secret_code",)
    # Is it possible to restrict streams values by applicant?
    # inlines = [InterviewStreamsInline]

    @meta(_("Accepted"))
    def get_accepted(self, obj):
        return _("Yes") if obj.is_accepted else _("No")

    @meta(_("Applicant"))
    def get_applicant(self, obj):
        return obj.applicant.get_full_name()

    @meta(_("City"))
    def get_campaign_city(self, obj):
        return obj.applicant.campaign.city


admin.site.register(Campaign, CampaignAdmin)
admin.site.register(Applicant, ApplicantAdmin)
admin.site.register(Test, OnlineTestAdmin)
admin.site.register(Exam, ExamAdmin)
admin.site.register(Interview, InterviewAdmin)
admin.site.register(InterviewAssignment, InterviewAssignmentAdmin)
admin.site.register(Contest, ContestAdmin)
admin.site.register(Comment, InterviewCommentAdmin)
admin.site.register(InterviewStream, InterviewStreamAdmin)
admin.site.register(InterviewSlot, InterviewSlotAdmin)
admin.site.register(InterviewInvitation, InterviewInvitationAdmin)
