from django.contrib import admin

from learning.models import Course, Semester, CourseOffering, Venue, \
    CourseClass, CourseNews

class CourseClassAdmin(admin.ModelAdmin):
    save_as = True
    date_hierarchy = 'date'
    list_filter = ['course_offering', 'venue', 'type']
    list_display = ['name', 'course_offering', 'date', 'venue', 'type_display']

class CourseNewsAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ['title', 'course_offering', 'created']

admin.site.register(Course)
admin.site.register(Semester)
admin.site.register(CourseOffering)
admin.site.register(Venue)
admin.site.register(CourseClass, CourseClassAdmin)
admin.site.register(CourseNews, CourseNewsAdmin)
