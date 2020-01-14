import pytest

from core.models import Branch
from core.tests.factories import BranchFactory
from core.utils import get_youtube_video_id, queryset_iterator, instance_memoize


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


@pytest.mark.django_db
def test_queryset_iterator(django_assert_num_queries):
    branches = BranchFactory.create_batch(10)
    qs = Branch.objects.filter(pk__gte=branches[0].pk)
    assert qs.count() == 10
    with django_assert_num_queries(0):
        # Negative chunk size has no sense
        list(queryset_iterator(qs, chunk_size=-1))
    with django_assert_num_queries(1):
        for b in qs:
            pass
    # 1 additional query for min and max PK aggregation
    with django_assert_num_queries(2):
        for b in queryset_iterator(qs, chunk_size=10):
            pass
    with django_assert_num_queries(2):
        for b in queryset_iterator(qs, chunk_size=100):
            pass
    with django_assert_num_queries(3):
        for b in queryset_iterator(qs, chunk_size=5):
            pass
    # Make sure use_offset=True preserves queryset ordering if provided
    with django_assert_num_queries(2):
        bs = list(queryset_iterator(qs.order_by("-order"),
                                    chunk_size=10, use_offset=True))
    bs.reverse()
    assert bs == branches


def test_instance_memoize():
    class A:
        def __init__(self):
            self.counter = -1

        @instance_memoize
        def foo(self, i):
            self.counter += 1
            return self.counter + i

    a = A()
    assert not hasattr(a, "_instance_memoize_cache")
    assert a.foo(1) == 1
    assert len(a.__dict__["_instance_memoize_cache"]) == 1
    assert a.foo(1) == 1
    del a.__dict__["_instance_memoize_cache"]
    assert a.foo(1) == 2
    a.counter = 42
    assert a.foo(1) == 2
    del a.__dict__["_instance_memoize_cache"]
    assert a.foo(1) == 44
    assert A.foo(a, 1) == 45
