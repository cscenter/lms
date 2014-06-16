var ends_at_touched = false;

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
        $textarea.removeProp("required");

        var editor = new EpicEditor({
            container: $container[0],
            textarea: $textarea[0],
            parser: marked,
            basePath: "/static/js/EpicEditor-v0.2.2",
            clientSideStorage: false,
            autogrow: {minHeight: 200},
            button: {bar: "show"},
            theme: {
                base: '/themes/base/epiceditor.css',
                editor: '/themes/editor/epic-light.css'
            }
        });

        editor.load();

        previewer = editor.getElement("previewer");
        var mathjax = previewer.createElement('script');
        mathjax.type = 'text/javascript';
        mathjax.src = 'http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML';
        previewer.body.appendChild(mathjax);

        var config = previewer.createElement('script');
        config.type = 'text/x-mathjax-config';
        config.text = "MathJax.Hub.Config({tex2jax: {inlineMath: [ ['$','$'] ], displayMath: [ ['$$','$$'] ], processEscapes: true}});";
        previewer.body.appendChild(config);

        editor.on('preview', function() {
            editor.getElement('previewerIframe').contentWindow.eval(
                'MathJax.Hub.Queue(["Typeset", MathJax.Hub]);');
        });
    });

    $("#id_ends_at").focus(function() {
        ends_at_touched = true;
    });

    // this is fragile as hell, didn't find a suitable library
    $("#id_starts_at").change(function() {
        var DELTA_MINUTES = 80;

        function pad(num, size) {
            var s = num+"";
            while (s.length < size) s = "0" + s;
            return s;
        }

        //if ($("#id_ends_at").val().length === 0) {
        if (!ends_at_touched) {
            var string_time = $(this).val();
            var matches = string_time.match(
                "([0-9]{2})([:\-])([0-9]{2})([:0-9\-]*)");
            if (matches !== null) {
                var hours = parseInt(matches[1]);
                var separator = matches[2];
                var minutes = parseInt(matches[3]);
                var maybe_seconds = matches[4];

                var raw_new_minutes = minutes + DELTA_MINUTES;
                var new_hours = (hours + Math.floor(raw_new_minutes / 60)) % 24;
                var new_minutes = raw_new_minutes % 60;

                $("#id_ends_at").val(pad(new_hours, 2)
                                     + separator
                                     + pad(new_minutes, 2)
                                     + maybe_seconds);
            } else {
                console.log("Can't parse " + string_time);
            }
        }
    });
});
