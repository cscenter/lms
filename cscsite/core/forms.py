import floppyforms as forms


class Ubereditor(forms.Textarea, object):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {})
        kwargs["attrs"].setdefault("class", "ubereditor")
        super(Ubereditor, self).__init__(*args, **kwargs)

    class Media:
        css = {"all": ["css/vendor/highlight-styles/solarized_light.css"]}
        js = ["//yastatic.net/underscore/1.6.0/underscore-min.js",
              "js/vendor/highlight.pack.js"]
