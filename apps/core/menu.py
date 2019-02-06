import re

from menu import MenuItem as _MenuItem


class MenuItem(_MenuItem):
    """
    Note:
        Only one item would be considered as selected.
        The last one in case of ambiguity.
    """
    for_staff = False
    visible_to = None
    # Additional check that item should be selected
    # Affects the parent visibility if `MENU_SELECT_PARENTS` setting is enabled
    # FIXME: remove relative patterns support? Or add the same to the excluded_patterns?
    selected_patterns = None
    excluded_patterns = None

    def __init__(self, title, url, **kwargs):
        super().__init__(title, url, **kwargs)
        if self.selected_patterns is not None:
            self.selected_patterns = [p.strip() for p in self.selected_patterns]
        if self.excluded_patterns is not None:
            self.excluded_patterns = [p.strip() for p in self.excluded_patterns]

    def check(self, request):
        """Evaluate if we should be visible for this request"""
        if self.visible_to is not None:
            user_groups = request.user.get_cached_groups()
            self.visible = bool(user_groups.intersection(self.visible_to))
        if callable(self.check_func):
            self.visible = self.check_func(request)
        if self.for_staff and not request.user.is_curator:
            self.visible = False

    def match_url(self, request):
        """match url determines if this is selected"""
        matched = False
        url = self.url
        # Relative URL means related view available on any subdomain
        if not url.startswith('http'):
            # For a correct comparison menu url with current path append scheme
            url = request.build_absolute_uri(location=url)
        current_path = request.build_absolute_uri()
        if self.exact_url:
            if re.match("%s$" % (url,), current_path):
                matched = True
        elif re.match("%s" % url, current_path):
            matched = True
        if not matched and self.selected_patterns is not None:
            for pattern in self.selected_patterns:
                # Relative path means pattern applicable to any subdomain
                if pattern.startswith('^/'):
                    pattern = (r"^" + request.build_absolute_uri(location='/') +
                               pattern[2:])
                # Deep copy for compiled regexp works in python 3.7+
                if re.compile(pattern).match(current_path):
                    matched = True
        elif matched and self.excluded_patterns is not None:
            for pattern in self.excluded_patterns:
                if re.compile(pattern).match(current_path):
                    matched = False
        return matched