var ends_at_touched = false;
var marks_sheet_unsaved = 0;

$(document).ready(function () {
    hljs.configure({tabReplace: '    '});

    marked.setOptions({
        highlight: function (code, lang) {
            return typeof lang != "undefined"
                ? hljs.highlight(lang, code).value
                : code;
        },
        smartypants: true
    });

    $("div.ubertext").each(function() {
        var target = this
          , $target = $(this);

        MathJax.Hub.Queue(["Typeset", MathJax.Hub, target, function() {
            target.innerHTML = marked(jQuery.trim(target.innerHTML));
            $target.find("pre").addClass("hljs");
        }]);
    });

    $("textarea.ubereditor").each(function(i) {
        var $textarea = $(this);
        var $container = $("<div/>").insertAfter($textarea);

        $textarea.hide();
        $textarea.removeProp("required");

        var editor = new EpicEditor({
            container: $container[0],
            textarea: $textarea[0],
            parser: null,
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

        var previewer = editor.getElement("previewer");
        var mathjax = previewer.createElement('script');
        mathjax.type = 'text/javascript';
        mathjax.src = '//cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML';
        previewer.body.appendChild(mathjax);
        previewer.body.appendChild(
            // re-use config from the top-level document
            $("[type^='text/x-mathjax-config']").get(0));

        editor.on('preview', function() {
            var contentDocument
                = editor.getElement('previewerIframe').contentDocument;
            var target = $("#epiceditor-preview", contentDocument).get(0);
            MathJax.Hub.Queue(["Typeset", MathJax.Hub, target, function() {
                target.innerHTML = marked(target.innerHTML);
            }]);
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

    if (marks_sheet_unsaved == 0) {
        $("#marks-sheet-save").attr("disabled", "disabled");
    }

    $(".marks-sheet-form-cell select").change(function() {
        $this = $(this);
        var current_value = $this.val();
        var saved_value = $this.next("input[type=hidden]").val();
        if (current_value != saved_value) {
            $this.parent().addClass("marks-sheet-unsaved-cell");
            marks_sheet_unsaved++;
            if (marks_sheet_unsaved > 0) {
                $("#marks-sheet-save").removeAttr("disabled");
            }
        } else {
            $this.parent().removeClass("marks-sheet-unsaved-cell");
            marks_sheet_unsaved--;
            if (marks_sheet_unsaved == 0) {
                $("#marks-sheet-save").attr("disabled", "disabled");
            }
        }
    });
});
