import datetime
from typing import NamedTuple


class SocialPost(NamedTuple):
    text: str
    date: datetime.datetime
    post_url: str
    thumbnail: str = ''
