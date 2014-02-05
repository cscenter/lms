$(document).ready(function () {
    hljs.configure({tabReplace: '    '});

    marked.setOptions({
        highlight: function (code, lang) {
            return hljs.highlight(lang, code).value;
        },
        smartypants: true
    });

    $("div.ubertext").each(function(i) {
        $e = $(this);
        $e.html(marked(jQuery.trim($e.html())));
        $e.find("pre").addClass("hljs");
    });
});