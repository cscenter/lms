from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.contrib.auth import get_user_model
from modeltranslation.admin import TranslationAdmin

from core.admin import UbereditorMixin, WiderLabelsMixin
from core.models import apply_related_spec
from .models import Course, Semester, CourseOffering, Venue, \
    CourseClass, CourseClassAttachment, CourseOfferingNews, \
    Assignment, AssignmentAttachment, AssignmentStudent, \
    AssignmentComment, Enrollment, NonCourseEvent, StudentProject, OnlineCourse


from .constants import PARTICIPANT_GROUPS


class RelatedSpecMixin(object):
    def get_queryset(self, request):
        qs = super(RelatedSpecMixin, self).get_queryset(request)
        return apply_related_spec(qs, self.related_spec)


class CourseAdmin(TranslationAdmin, UbereditorMixin, admin.ModelAdmin):
    pass


class CourseOfferingAdmin(UbereditorMixin, WiderLabelsMixin, TranslationAdmin,
                          admin.ModelAdmin):
    list_filter = ['course', 'semester']
    list_display = ['course', 'semester', 'is_published_in_video', 'is_open']


class CourseClassAttachmentAdmin(admin.ModelAdmin):
    list_filter = ['course_class']
    list_display = ['course_class', '__str__']


class CourseClassAttachmentInline(admin.TabularInline):
    model = CourseClassAttachment


class CourseClassAdmin(UbereditorMixin, admin.ModelAdmin):
    save_as = True
    date_hierarchy = 'date'
    list_filter = ['course_offering', 'venue', 'type']
    list_display = ['name', 'course_offering', 'date', 'venue', 'type']
    inlines = [CourseClassAttachmentInline]


class CourseOfferingNewsAdmin(UbereditorMixin, admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ['title', 'course_offering', 'created']


class VenueAdmin(UbereditorMixin, admin.ModelAdmin):
    pass


class AssignmentAdmin(UbereditorMixin, admin.ModelAdmin):
    list_display = ['title', 'course_offering', 'created', 'deadline_at']
    list_filter = ['course_offering']

    def get_readonly_fields(self, request, obj=None):
        return ['course_offering'] if obj else []


class AssignmentCommentAdmin(RelatedSpecMixin,
                             UbereditorMixin,
                             admin.ModelAdmin):
    readonly_fields = ['assignment_student']
    related_spec = {'select': [('assignment_student',
                                [('assignment',
                                  [('course_offering',
                                    ['semester', 'course'])]),
                                 'student'])]}


class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course_offering', 'grade', 'grade_changed']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['student', 'course_offering', 'grade_changed', 'modified']
        else:
            return ['grade_changed', 'modified']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'student':
            kwargs['queryset'] = (get_user_model().objects
                                  .filter(groups__in=[
                                        PARTICIPANT_GROUPS.STUDENT_CENTER,
                                        PARTICIPANT_GROUPS.VOLUNTEER]))
        return (super(EnrollmentAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))


class AssignmentStudentAdmin(RelatedSpecMixin,
                             admin.ModelAdmin):
    list_display = ['student', 'assignment', 'grade', 'grade_changed', 'state']
    related_spec = {'select': [('assignment',
                                [('course_offering', ['semester', 'course'])]),
                               'student']}

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['student', 'assignment', 'grade_changed', 'state']
        else:
            return ['grade_changed', 'state']


class NonCourseEventAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    list_filter = ['venue']
    list_display = ['name', 'date', 'venue']


class StudentProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'project_type', 'semester']
    list_filter = ['semester']


class OnlineCourseAdmin(UbereditorMixin, admin.ModelAdmin):
    pass


admin.site.register(Course, CourseAdmin)
admin.site.register(OnlineCourse, OnlineCourseAdmin)
admin.site.register(Semester)
admin.site.register(CourseOffering, CourseOfferingAdmin)
admin.site.register(Venue, VenueAdmin)
admin.site.register(CourseClass, CourseClassAdmin)
admin.site.register(CourseClassAttachment, CourseClassAttachmentAdmin)
admin.site.register(CourseOfferingNews, CourseOfferingNewsAdmin)
admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(AssignmentAttachment)
admin.site.register(AssignmentStudent, AssignmentStudentAdmin)
admin.site.register(AssignmentComment, AssignmentCommentAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
admin.site.register(NonCourseEvent, NonCourseEventAdmin)
admin.site.register(StudentProject, StudentProjectAdmin)
