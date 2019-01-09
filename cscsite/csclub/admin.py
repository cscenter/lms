from django.contrib import admin

from international_schools.admin import InternationalSchoolAdmin
from international_schools.models import InternationalSchool

admin.site.register(InternationalSchool, InternationalSchoolAdmin)
