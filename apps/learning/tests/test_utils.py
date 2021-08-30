from learning.utils import split_on_condition


def test_split_list():
    xs = [1, 2, 3, 4]
    assert ([1, 3], [2, 4]) == split_on_condition(xs, lambda x: x % 2 != 0)
    assert (xs, []) == split_on_condition(xs, lambda x: True)
    assert ([], xs) == split_on_condition(xs, lambda x: False)
