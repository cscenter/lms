import floppyforms as forms


class Ubereditor(forms.Textarea, object):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {})
        kwargs["attrs"].setdefault("class", "ubereditor")
        super(Ubereditor, self).__init__(*args, **kwargs)

    class Media:  # pylint: disable=no-init,old-style-class
        css = {"all": ["css/highlight-styles/solarized_light.css"]}
        js = ["//code.jquery.com/jquery-1.10.2.min.js",
              "js/highlight.pack.js",
              "js/main.js",
              "js/EpicEditor-v0.2.2/js/epiceditor.min.js",
              "js/marked.js"]
