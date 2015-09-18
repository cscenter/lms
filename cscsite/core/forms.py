import floppyforms as forms


class Ubereditor(forms.Textarea, object):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {})
        kwargs["attrs"].setdefault("class", "ubereditor")
        super(Ubereditor, self).__init__(*args, **kwargs)
