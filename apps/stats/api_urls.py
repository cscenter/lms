from django.conf.urls import include, url

# Run `./manage.py collectstatic_js_reverse` to update js file with urls
urlpatterns = [
    url(r'^stats/', include([
        url(r'^learning/', include('stats.learning.api_urls')),
        url(r'^admission/', include('stats.admission.api_urls')),
    ]))
]
