from django.conf import settings
from django.core.cache import cache

from micawber.providers import Provider, bootstrap_basic

from bs4 import BeautifulSoup


class CustomSlideShareProvider(Provider):
    """
    Slideshare oembed service returns html with additional information
    about slides title and author. Hide them and fix width x height iframe
    """

    def handle_response(self, response, url):
        json_data = super(CustomSlideShareProvider,
                          self).handle_response(response, url)
        soup = BeautifulSoup(json_data["html"], 'html.parser')
        soup.iframe["width"] = settings.MICAWBER_DEFAULT_SETTINGS["maxwidth"]
        soup.iframe["height"] = settings.MICAWBER_DEFAULT_SETTINGS["maxheight"]
        json_data["html"] = str(soup.iframe)
        return json_data
    # TODO: replace http request with https


# Oembed provider registry
pr = bootstrap_basic(cache)
# Replace default slideshare providers with customs
pr.unregister('http://www.slideshare.net/[^\/]+/\S+')
pr.unregister('http://slidesha\.re/\S*')
pr.register('http://www.slideshare.net/[^\/]+/\S+',
            CustomSlideShareProvider('http://www.slideshare.net/api/oembed/2',
                                     format="jsonp"))
pr.register('http://slidesha\.re/\S*',
            CustomSlideShareProvider('http://www.slideshare.net/api/oembed/2',
                                     format="jsonp"))

pr.register(r"https?://(www)?video.yandex.ru/\S*",
            Provider("https://video.yandex.ru/oembed"))

oembed_providers = pr