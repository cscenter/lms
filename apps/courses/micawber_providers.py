import logging

from django.conf import settings
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key

from micawber.providers import Provider, bootstrap_basic

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


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
pr.unregister('https?://www.slideshare.net/[^\/]+/\S+')
pr.unregister('https?://slidesha\.re/\S*')
pr.register('https?://www.slideshare.net/[^\/]+/\S+',
            CustomSlideShareProvider('https://www.slideshare.net/api/oembed/2',
                                     format="jsonp"))
pr.register('https?://slidesha\.re/\S*',
            CustomSlideShareProvider('https://www.slideshare.net/api/oembed/2',
                                     format="jsonp"))

pr.register(r"https?://(www)?video.yandex.ru/\S*",
            Provider("https://video.yandex.ru/oembed"))

oembed_providers = pr


EMBED_IFRAME_TEMPLATE = """
<iframe src="{}" allowfullscreen="1" width="{}" height="{}"></iframe>"""
EMBED_IFRAME_CACHE_TIME = 3600 * 2


def get_oembed_data(url, default=False):
    from micawber.contrib.mcdjango import extract_oembed
    if not url:
        return None
    embed = None
    try:
        [(_url, embed)] = extract_oembed(url)
    except ValueError:
        if default:
            embed = {
                "html": EMBED_IFRAME_TEMPLATE.format(
                    url,
                    settings.MICAWBER_DEFAULT_SETTINGS["maxwidth"],
                    settings.MICAWBER_DEFAULT_SETTINGS["maxheight"])
            }
        else:
            logger.warning("Can't extract oembed data from url {}".format(url))
    return embed


def get_oembed_html(url, cache_key, use_default):
    cache_key = make_template_fragment_key(cache_key, [url])
    html = cache.get(cache_key)
    if html is None:
        embed = get_oembed_data(url, default=use_default)
        html = embed.get("html", "") if embed else ""
        cache.set(cache_key, html, EMBED_IFRAME_CACHE_TIME)
    return html
