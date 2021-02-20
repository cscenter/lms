from rest_framework.fields import ChoiceField


class AliasedChoiceField(ChoiceField):
    """
    Accepts list of (external_key, internal_key, [display_name]) tuples as *choices*.
    When *display_name* is omitted *internal_key* will be used as a display name for ChoiceField widget.
    """

    def __init__(self, choices, **kwargs):
        self._aliases = {}  # external_key => internal_key
        if choices:
            if len(choices[0]) == 3:
                self._aliases = {external_key: internal_key for external_key, internal_key, display_name in choices}
                choices = [(external_key, display_name) for external_key, internal_key, display_name in choices]
            else:
                self._aliases = {external_key: internal_key for external_key, internal_key in choices}
        self._aliases_rev = {v: k for k, v in self._aliases.items()}
        super().__init__(choices, **kwargs)

    def to_internal_value(self, data):
        if data == '' and self.allow_blank:
            return ''

        external_key = super().to_internal_value(data)
        return self._aliases[external_key]

    def to_representation(self, value):
        return self._aliases_rev[value]
