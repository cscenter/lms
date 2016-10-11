import floppyforms.__future__ as forms


class Ubereditor(forms.Textarea, object):
    # template_name = 'ubertextarea.html'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {})
        kwargs["attrs"].setdefault("class", "ubereditor")
        super(Ubereditor, self).__init__(*args, **kwargs)
