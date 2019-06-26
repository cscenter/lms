import pytest

from core.utils import get_youtube_video_id


def test_get_youtube_video_id():
    assert get_youtube_video_id('https://youtu.be/sxnSFdRECas') == 'sxnSFdRECas'
    assert get_youtube_video_id('https://youtu.be/sxnSFdRECas?v=42') == 'sxnSFdRECas'
    # Not valid url btw
    assert get_youtube_video_id('https://youtu.be/sxnSFdRECas/what?') == 'sxnSFdRECas'
    assert get_youtube_video_id('youtu.be/sxnSFdRECas?') == 'sxnSFdRECas'
    assert get_youtube_video_id('https://ya.ru/watch?v=0lZJicHYJXM') is None
    assert get_youtube_video_id('https://youtube.com/watch?v=0lZJicHYJXM') == '0lZJicHYJXM'
    assert get_youtube_video_id('https://www.youtube.com/watch?v=0lZJicHYJXM') == '0lZJicHYJXM'
    assert get_youtube_video_id('youtube.com/embed/8SPq-9kS69M') == '8SPq-9kS69M'
    assert get_youtube_video_id('https://www.youtube-nocookie.com/embed/8SPq-9kS69M') == '8SPq-9kS69M'
