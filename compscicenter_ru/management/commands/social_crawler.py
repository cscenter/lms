# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from typing import NamedTuple

from django.conf import settings
from django.core.cache import caches
from django.core.management.base import BaseCommand
from requests import RequestException

from api.providers.instagram import InstagramAPI, InstagramAPIException
from api.providers.vk import VkOpenAPI, CSCENTER_GROUP_ID, VkAPIException
from compscicenter_ru.views import IndexView
from core.models import SiteConfiguration

logger = logging.getLogger(__name__)


CACHE_EXPIRES_IN = None  # Manually clean cache on each command run


class SocialPost(NamedTuple):
    text: str
    date: datetime
    post_url: str
    thumbnail: str = ''


class Command(BaseCommand):
    help = 'Grab last N posts from social networks: [vk.com, instagram.com]'

    def handle(self, *args, **options):
        # Note: better to store data in file-based cache
        cache = caches['social_networks']

        vk_api = VkOpenAPI()
        try:
            json_data = vk_api.get_wall(owner_id=CSCENTER_GROUP_ID, count=2)
            data_to_cache = []
            for news in json_data["response"]["items"]:
                url = f"https://vk.com/compscicenter?w=wall{news['owner_id']}_{news['id']}"
                # Process repost
                if not news["text"] and "copy_history" in news:
                    # 0 index stores the post from which we made a repost
                    post_text = news["copy_history"][0]["text"]
                else:
                    post_text = news["text"]
                post = SocialPost(text=post_text,
                                  date=datetime.fromtimestamp(news['date']),
                                  post_url=url)
                data_to_cache.append(post)
            cache.set(IndexView.VK_CACHE_KEY,
                      data_to_cache, CACHE_EXPIRES_IN)
        except RequestException:
            logger.error("vk.com: Network connection problem")
        except VkAPIException:
            pass

        site_settings = (SiteConfiguration.objects
                         .get(site_id=settings.SITE_ID))
        if not site_settings.instagram_access_token:
            logger.info("Instagram API access token is not provided. Exit")
            return

        access_token = SiteConfiguration.decrypt(site_settings.instagram_access_token)
        instagram_client = InstagramAPI(access_token=access_token)
        try:
            json_data = instagram_client.get_recent_posts()
            data_to_cache = []
            for post in json_data["data"]:
                thumbnail = post['thumbnail_url'] if post['media_type'] == 'VIDEO' else post['media_url']
                to_cache = SocialPost(text=post['caption'],
                                      date=datetime.strptime(post['timestamp'], "%Y-%m-%dT%H:%M:%S%z"),
                                      post_url=post['permalink'],
                                      thumbnail=thumbnail)
                data_to_cache.append(to_cache)
                break
            cache.set(IndexView.INSTAGRAM_CACHE_KEY, data_to_cache,
                      CACHE_EXPIRES_IN)
        except RequestException:
            logger.error("instagram.com: Network connection problem")
        except InstagramAPIException:
            pass
        # Long-lived token expires in 60 days
        data = instagram_client.refresh_access_token()
        new_token = SiteConfiguration.encrypt(data['access_token'])
        SiteConfiguration.objects.filter(pk=site_settings.pk).update(instagram_access_token=new_token)
