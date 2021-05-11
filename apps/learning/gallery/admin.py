from __future__ import absolute_import, unicode_literals

from mptt.admin import MPTTModelAdmin

from django.contrib import admin

from courses.models import Course

from .models import Album, Image


class InlineImageAdmin(admin.TabularInline):
    model = Image
    fieldsets = ((None, {
        'fields': ['image', 'user', 'title', 'order', 'album']
    }),)
    raw_id_fields = ('user', )
    extra = 0


class AlbumAdmin(MPTTModelAdmin):
    mptt_level_indent = 20
    list_display = ('name', 'order')
    inlines = [InlineImageAdmin]


class ImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'order', 'album', 'width', 'height')
    raw_id_fields = ('user', )
    list_filter = ('album', )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'course':
            kwargs['queryset'] = (Course.objects
                                  .select_related("meta_course", "semester"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def width(self, obj):
        try:
            return obj.image.width
        except IOError:
            return None

    def height(self, obj):
        try:
            return obj.image.height
        except IOError:
            return None


admin.site.register(Album, AlbumAdmin)
admin.site.register(Image, ImageAdmin)
