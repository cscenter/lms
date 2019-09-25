from django.conf.urls import include, url

app_name = 'api'
# Run `./manage.py collectstatic_js_reverse` to update js file with urls
urlpatterns = [
    url(r'^v1/stats/', include([
        url(r'^learning/', include('stats.learning.api_urls')),
        url(r'^admission/', include('stats.admission.api_urls')),
    ]))
]
