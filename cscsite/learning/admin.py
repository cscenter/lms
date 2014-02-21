from django.contrib import admin

from learning.models import Course, Semester, CourseOffering

admin.site.register(Course)
admin.site.register(Semester)
admin.site.register(CourseOffering)
