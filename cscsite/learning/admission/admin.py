from django.db import models
from django.db.models import TextField
from django.utils import timezone
from jsonfield import JSONField
from prettyjson import PrettyJSONWidget
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from import_export.admin import ExportMixin

from core.admin import CityAwareModelForm, CityAwareAdminSplitDateTimeWidget, \
    CityAwareSplitDateTimeField, meta
from core.widgets import AdminRichTextAreaWidget
from core.utils import admin_datetime
from learning.admission.forms import InterviewStreamChangeForm
from learning.admission.import_export import OnlineTestRecordResource, \
    ExamRecordResource
from learning.admission.models import Campaign, Interview, Applicant, Test, \
    Exam, Comment, InterviewAssignment, Contest, InterviewSlot, InterviewStream, \
    InterviewInvitation


class CampaignListFilter(admin.SimpleListFilter):
    title = _('Campaign')
    parameter_name = 'campaign_id__exact'

    def lookups(self, request, model_admin):
        campaigns = (Campaign.objects
                     .select_related("city")
                     .order_by("-city_id", "-year"))
        return [(c.pk, str(c)) for c in campaigns]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(**{self.parameter_name: self.value()})
        else:
            return queryset


class CampaignAdmin(admin.ModelAdmin):
    form = CityAwareModelForm
    list_display = ['year', 'city', 'current']
    list_filter = ['city']
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

    def get_campaign(self, obj):
        return obj.applicant.campaign
    get_campaign.short_description = _("Campaign")

    def get_queryset(self, request):
        qs = super(OnlineTestAdmin, self).get_queryset(request)
        return qs.select_related('applicant',
                                 'applicant__campaign',
                                 'applicant__campaign__city')

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'applicant':
            kwargs['queryset'] = (
                Applicant.objects
                         .select_related("campaign", "campaign__city")
                         .order_by("surname"))
        return (super(OnlineTestAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))


class ExamAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = ExamRecordResource
    list_display = ['__str__', 'score', 'yandex_contest_id']
    search_fields = ['applicant__yandex_id', 'applicant__surname',
                     'applicant__first_name', 'yandex_contest_id']
    list_filter = ['applicant__campaign']
    formfield_overrides = {
        JSONField: {'widget': PrettyJSONWidget}
    }

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
    list_display = ['id', 'yandex_id', 'surname', 'first_name', 'campaign', 'created']
    list_filter = [CampaignListFilter, 'status']
    search_fields = ['yandex_id', 'yandex_id_normalize', 'stepic_id',
                     'first_name', 'surname', 'email']
    readonly_fields = ['yandex_id_normalize']

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
    list_display = ['contest_id', 'campaign']
    list_filter = [CampaignListFilter]

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

    def has_add_permission(self, request):
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


class InterviewInvitationAdmin(admin.ModelAdmin):
    form = CityAwareModelForm
    formfield_overrides = {
        models.DateTimeField: {
            'widget': CityAwareAdminSplitDateTimeWidget,
            'form_class': CityAwareSplitDateTimeField
        }
    }
    model = InterviewInvitation
    list_select_related = ["applicant", "applicant__campaign__city"]
    list_display = ['date', 'get_applicant', 'get_campaign_city', 'get_accepted']
    raw_id_fields = ("interview", "applicant")
    readonly_fields = ("secret_code",)

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
