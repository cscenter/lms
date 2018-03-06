from typing import NamedTuple


class SocialPost(NamedTuple):
    text: str
    date: int
    thumbnail: str = ''
