from django.contrib import admin

from universities.models import City, Country, Faculty, University


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'country')
    list_filter = ['country']


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ('name', 'external_id', 'city')
    search_fields = ('display_name',)


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_select_related = ['university']
    list_display = ('name', 'external_id', 'university')
    raw_id_fields = ['university']
