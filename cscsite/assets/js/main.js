$(document).ready(function () {
    hljs.configure({tabReplace: '    '});

    marked.setOptions({
        highlight: function (code, lang) {
            return hljs.highlight(lang, code).value;
        },
        smartypants: true
    });

    $("div.ubertext").each(function(i) {
        var $e = $(this);
        $e.html(marked(jQuery.trim($e.html())));
        $e.find("pre").addClass("hljs");
    });

    $("textarea.ubereditor").each(function(i) {
        var $textarea = $(this);
        var $container = $("<div/>").insertAfter($textarea);

        $textarea.hide();

        var editor = new EpicEditor({
            container: $container[0],
            textarea: $textarea[0],
            parser: marked,
            basePath: "/static/js/EpicEditor-v0.2.2",
            clientSideStorage: false,
            autogrow: {minHeight: 200}
        });

        editor.load();

        previewer = editor.getElement("previewer");
        var mathjax = previewer.createElement('script');
        mathjax.type = 'text/javascript';
        mathjax.src = 'http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML';
        previewer.body.appendChild(mathjax);

        var config = previewer.createElement('script');
        config.type = 'text/x-mathjax-config';
        config.text = "MathJax.Hub.Config({tex2jax: {inlineMath: [ ['$','$'], ['\\(','\\)'] ], processEscapes: true}});";
        previewer.body.appendChild(config);

        editor.on('preview', function() {
            editor.getElement('previewerIframe').contentWindow.eval(
                'MathJax.Hub.Queue(["Typeset", MathJax.Hub]);');
        });
    });
});