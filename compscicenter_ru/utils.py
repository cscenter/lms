from typing import List

import attr


@attr.s(auto_attribs=True, slots=True)
class Tab:
    target: str = attr.ib()
    name: str = attr.ib()
    active: bool = False
    url: str = '#'
    order: int = 0


class TabList:
    def __init__(self, tabs: List[Tab] = None):
        self._tabs = {t.target: t for t in tabs if t} if tabs else {}

    def add(self, tab: Tab):
        self._tabs[tab.target] = tab

    def set_active(self, target) -> None:
        for t in self._tabs.values():
            t.active = False
        if target in self._tabs:
            # TODO: warn if tab not found
            self._tabs[target].active = True

    def sort(self, key=None):
        """If **key** is None, sort by tab.order attribute"""
        key = key or (lambda t: t.order)
        new_order = list((key(t), t.target) for t in self._tabs.values())
        new_order.sort()
        self._tabs = {target: self._tabs[target] for _, target in new_order}

    def items(self):
        return self._tabs.items()

    def __iter__(self):
        return iter(self._tabs.values())

    def __getitem__(self, target):
        # TODO: support indexing by int since dict in python > 3.5 is ordered
        return self._tabs[target]

    def __contains__(self, item):
        return item in self._tabs
    
    def __len__(self):
        return len(self._tabs)
