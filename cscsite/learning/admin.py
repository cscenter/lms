from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.contrib.auth import get_user_model

from core.admin import UbereditorMixin, WiderLabelsMixin
from .models import Course, Semester, CourseOffering, Venue, \
    CourseClass, CourseClassAttachment, CourseOfferingNews, \
    Assignment, AssignmentStudent, AssignmentComment, \
    Enrollment, OverallGrade


class CourseAdmin(UbereditorMixin, admin.ModelAdmin):
    pass


class CourseOfferingAdmin(UbereditorMixin,
                          WiderLabelsMixin,
                          admin.ModelAdmin):
    list_filter = ['course', 'semester']
    list_display = ['course', 'semester']


class CourseClassAttachmentAdmin(admin.ModelAdmin):
    list_filter = ['course_class']
    list_display = ['course_class', '__str__']


class CourseClassAttachmentInline(admin.TabularInline):
    model = CourseClassAttachment


class CourseClassAdmin(UbereditorMixin, admin.ModelAdmin):
    save_as = True
    date_hierarchy = 'date'
    list_filter = ['course_offering', 'venue', 'type']
    list_display = ['name', 'course_offering', 'date', 'venue', 'type_display']
    inlines = [
        CourseClassAttachmentInline]


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


class AssignmentCommentAdmin(UbereditorMixin, admin.ModelAdmin):
    pass


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
                                  .filter(groups__name='Student'))
        return (super(EnrollmentAdmin, self)
                .formfield_for_foreignkey(db_field, request, **kwargs))


class OverallGradeAdmin(admin.ModelAdmin):
    list_display = ['student', 'grade', 'grade_changed']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['student', 'grade_changed']
        else:
            return ['grade_changed']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'student':
            kwargs['queryset'] = (get_user_model().objects
                                  .filter(groups__name='Student'))
            return (super(OverallGradeAdmin, self)
                    .formfield_for_foreignkey(db_field, request, **kwargs))


class AssignmentStudentAdmin(admin.ModelAdmin):
    list_display = ['student', 'assignment', 'state', 'state_changed']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['student', 'assignment', 'state_changed']
        else:
            return ['state_changed']


admin.site.register(Course, CourseAdmin)
admin.site.register(Semester)
admin.site.register(CourseOffering, CourseOfferingAdmin)
admin.site.register(Venue, VenueAdmin)
admin.site.register(CourseClass, CourseClassAdmin)
admin.site.register(CourseClassAttachment, CourseClassAttachmentAdmin)
admin.site.register(CourseOfferingNews, CourseOfferingNewsAdmin)
admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(AssignmentStudent, AssignmentStudentAdmin)
admin.site.register(AssignmentComment, AssignmentCommentAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
admin.site.register(OverallGrade, OverallGradeAdmin)
