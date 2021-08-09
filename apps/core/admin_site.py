from typing import Any, List, Union

from loginas.views import user_login, user_logout

from django.apps import apps
from django.contrib.admin import AdminSite
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import URLPattern, URLResolver, include, path, re_path
from django.views.decorators.cache import never_cache

URLPath = Union[URLResolver, URLPattern]


class BaseAdminSite(AdminSite):
    enable_nav_sidebar = False

    def get_urls(self) -> List[URLPath]:
        base_patterns: List[URLPath] = super().get_urls()
        url_patterns: List[URLPath] = []

        if apps.is_installed('loginas'):
            url_patterns.extend([
                re_path(r"^login/user/(?P<user_id>.+)/$", user_login, name='loginas-user-login'),
                path('logout/', user_logout, name='loginas-logout'),
            ])

        if apps.is_installed('django_rq'):
            url_patterns.append(path('django-rq/', include('django_rq.urls')))

        if apps.is_installed('announcements'):
            from announcements.views import AnnouncementTagAutocomplete
            url_patterns += [
                path('announcements/tags-autocomplete/', AnnouncementTagAutocomplete.as_view(), name='announcements_tags_autocomplete')
            ]

        if apps.is_installed('library'):
            from library.views import BookTagAutocomplete
            url_patterns += [
                path('library/tags-autocomplete/', BookTagAutocomplete.as_view(), name='library_tags_autocomplete')
            ]

        if apps.is_installed('info_blocks'):
            from info_blocks.views import InfoBlockTagAutocomplete
            url_patterns += [
                path('info_blocks/tags-autocomplete/', InfoBlockTagAutocomplete.as_view(), name='info_blocks_tags_autocomplete')
            ]

        if apps.is_installed('ckeditor_uploader'):
            from ckeditor_uploader.views import browse, upload
            url_patterns.extend([
                path('ckeditor/upload/', staff_member_required(upload), name='ckeditor_upload'),
                path('ckeditor/browse/', never_cache(staff_member_required(browse)), name='ckeditor_browse'),
            ])

        return url_patterns + base_patterns
