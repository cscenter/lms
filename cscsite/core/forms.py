import floppyforms as forms


class Ubereditor(forms.Textarea, object):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {})
        kwargs["attrs"].setdefault("class", "ubereditor")
        super(Ubereditor, self).__init__(*args, **kwargs)

    class Media:
        css = {"all": ["css/highlight-styles/solarized_light.css"]}
        js = ["//yastatic.net/underscore/1.6.0/underscore-min.js",
              "js/highlight.pack.js",
              "js/main.js",
              # assuming that Django will include JS files in this order,
              # because Marked creates global object and we need to override
              # epiceditor's one
              "js/EpicEditor-v0.2.2/js/epiceditor.min.js",
              "js/marked.js"]
