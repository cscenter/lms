from django.core.cache import cache

from micawber.providers import Provider, bootstrap_basic

oembed_providers = bootstrap_basic(cache)

oembed_providers.register(r"https?://(www)?video.yandex.ru/\S*",
                          Provider("https://video.yandex.ru/oembed"))
