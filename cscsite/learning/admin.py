from __future__ import absolute_import, unicode_literals

from django.contrib import admin

from core.admin import UbereditorMixin
from .models import Course, Semester, CourseOffering, Venue, \
    CourseClass, CourseOfferingNews, \
    Assignment, AssignmentStudent, AssignmentComment, \
    Enrollment


class CourseAdmin(UbereditorMixin, admin.ModelAdmin):
    pass


class CourseOfferingAdmin(UbereditorMixin, admin.ModelAdmin):
    list_filter = ['course', 'semester']
    list_display = ['course', 'semester']



class CourseClassAdmin(UbereditorMixin, admin.ModelAdmin):
    save_as = True
    date_hierarchy = 'date'
    list_filter = ['course_offering', 'venue', 'type']
    list_display = ['name', 'course_offering', 'date', 'venue', 'type_display']


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
    list_display = ['student', 'course_offering']


class AssignmentStudentAdmin(admin.ModelAdmin):
    list_display = ['student', 'assignment', 'state', 'state_changed']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['assignment', 'student', 'state_changed']
        else:
            return ['state_changed']


admin.site.register(Course, CourseAdmin)
admin.site.register(Semester)
admin.site.register(CourseOffering, CourseOfferingAdmin)
admin.site.register(Venue, VenueAdmin)
admin.site.register(CourseClass, CourseClassAdmin)
admin.site.register(CourseOfferingNews, CourseOfferingNewsAdmin)
admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(AssignmentStudent, AssignmentStudentAdmin)
admin.site.register(AssignmentComment, AssignmentCommentAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
