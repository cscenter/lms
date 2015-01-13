var ends_at_touched = false;
var marks_sheet_unsaved = 0;

$(document).ready(function () {
    //
    // localStorage-related helpers
    //

    var loadMap = function(name) {
        var map = window.localStorage.getItem(name);
        if (map !== null) {
            return JSON.parse(map);
        } else {
            return {};
        };
    };

    var saveMap = function(name, map) {
        window.localStorage.setItem(name, JSON.stringify(map));
    };

    // map from filename to hash
    var savedHashes = loadMap("savedHashes");
    // map from hash to date when it was seen
    var seenHashes = loadMap("seenHashes");

    //
    // Ubertext
    //

    hljs.configure({tabReplace: '    '});

    var renderer = new marked.Renderer();
    renderer.codespan = function (code) {
        return "<code>" + _.unescape(code) + "</code>";
    };

    marked.setOptions({
        renderer: renderer,
        highlight: function (code, lang) {
            var unescaped = _.unescape(code);
            return typeof lang != "undefined"
                ? hljs.highlight(lang, unescaped).value
                : unescaped;
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

        if (target.dataset.hash !== undefined) {
            seenHashes[target.dataset.hash] = new Date();
            saveMap("seenHashes", seenHashes);
        }
    });

    //
    // Ubereditors
    //

    var $ubereditors = $("textarea.ubereditor");
    var ubereditorRestoration = true;
    if ($ubereditors.length > 1) {
        console.warn("more than one Ubereditor on page, " +
                     "text restoration may be buggy");
    }

    // eliminate old or definitely succeeded (because their hash has been seen)
    // epiceditor "files"
    if ($ubereditors.length > 0 && window.hasOwnProperty("localStorage")) {
        (function() {
            var editor = new EpicEditor();
            var files = editor.getFiles(null, true);
            for (var filename in files) {
                if (files.hasOwnProperty(filename)) {
                    var modified = new Date(files[filename].modified);
                    var now = new Date();
                    var hoursOld = Math.floor((now - modified)
                                              / (1000 * 60 * 60));
                    var hash;
                    if (filename in savedHashes) {
                        hash = savedHashes[filename];
                    } else {
                        console.warn("filename " + filename
                                     + " not found in savedHashes");
                        hash = "";
                    };

                    if ((hoursOld > 24) || (hash in seenHashes)) {
                        editor.remove(filename);
                        delete savedHashes[filename];
                        delete seenHashes[hash];
                        saveMap("savedHashes", savedHashes);
                        saveMap("seenHashes", seenHashes);
                    };
                };
            };
        })();
    };

    $ubereditors.each(function(i) {
        var $textarea = $(this);
        var $container = $("<div/>").insertAfter($textarea);
        var shouldFocus = false;

        $textarea.hide();
        shouldFocus = $textarea.prop("autofocus");
        $textarea.removeProp("required");

        var opts = {
            container: $container[0],
            textarea: $textarea[0],
            parser: null,
            focusOnLoad: shouldFocus,
            basePath: "/static/js/EpicEditor-v0.2.2",
            clientSideStorage: ubereditorRestoration,
            autogrow: {minHeight: 200},
            button: {bar: "show"},
            theme: {
                base: '/themes/base/epiceditor.css',
                editor: '/themes/editor/epic-light.css'
            }
        };

        var filename = (window.location.pathname.replace(/\//g, "_")
                        + "_" + i.toString());
        if (ubereditorRestoration) {
            opts['file'] = {
                name: filename,
                defaultContent: "",
                autoSave: 1000
            };
        };

        var editor = new EpicEditor(opts);

        if (ubereditorRestoration) {
            editor.on('autosave', function() {
                var text = editor.exportFile();
                var hash = CryptoJS.MD5(text).toString();
                savedHashes[filename] = hash;
                saveMap("savedHashes", savedHashes);
            });
        }

        editor.load();

        var previewer = editor.getElement("previewer");
        var mathjax = previewer.createElement('script');
        mathjax.type = 'text/javascript';
        mathjax.src = '//cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML';
        previewer.body.appendChild(mathjax);
        previewer.body.appendChild(
            // re-use config from the top-level document
            $("[type^='text/x-mathjax-config']").clone().get(0));

        editor.on('preview', function() {
            var contentDocument
                = editor.getElement('previewerIframe').contentDocument;
            var target = $("#epiceditor-preview", contentDocument).get(0);
            MathJax.Hub.Queue(["Typeset", MathJax.Hub, target, function() {
                target.innerHTML = marked(target.innerHTML);
            }]);
        });
    });

    //
    // Course class editing
    //

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

    //
    // Marks sheet (for teacher's one and staff's)
    //

    if (marks_sheet_unsaved == 0) {
        $("#marks-sheet-save").attr("disabled", "disabled");
    }

    $(".marks-table.teacher").on('change', 'input,select', function (e) {
        $this = $(this);
        $target = $(e.target)
        $csv_link = $(".marks-sheet-csv-link");
        var current_value = $target.val();
        var saved_value = $target.next("input[type=hidden]").val();
        if (current_value != saved_value) {
            $target.parent().addClass("marks-sheet-unsaved-cell");
            marks_sheet_unsaved++;
            if (marks_sheet_unsaved > 0) {
                $("#marks-sheet-save").removeAttr("disabled");
                $csv_link.addClass("disabled");
            }
        } else {
            $target.parent().removeClass("marks-sheet-unsaved-cell");
            marks_sheet_unsaved--;
            if (marks_sheet_unsaved == 0) {
                $("#marks-sheet-save").attr("disabled", "disabled");
                $csv_link.removeClass("disabled");
            }
        }
    })

    // see this http://stackoverflow.com/a/8641208 for discussion
    // about the following hack
    $('.marks-table').each(function (i) {
        $(this).find('tr').each(function() {
            $(this).find('td').each(function(j) {
                // order marks sheets for different course offerings properly
                var idx = j + 1000 * (i + 1);
                $(this).find('input,select').attr('tabindex', idx);
            });
        });
    });

    $('.marks-table').on('mousewheel', 'input[type=number]', function (e) {
        this.blur();
    });

    $('.marks-table.teacher').on('focus', 'input,select', function (e) {
        $(this).closest("tr").addClass("active");
        var tdIdx = $(this).closest("td").index();
        ($(this).closest(".marks-table")
         .find("tr > td.content:nth-child(" + (tdIdx + 1) +")")
         .addClass("active"));
    });

    $('.marks-table.teacher').on('blur', 'input,select', function (e) {
        $(this).closest(".marks-table").find("td,tr").removeClass("active");
    });

    $('.marks-table.staff').on('click', 'td.content', function (e) {
        $(this).closest(".marks-table").addClass("focused");
        $(this).closest(".marks-table").find("td,tr").removeClass("active");
        $(this).closest("tr").addClass("active");
        var tdIdx = $(this).closest("td").index();
        ($(this).closest(".marks-table")
         .find("tr > td.content:nth-child(" + (tdIdx + 1) +")")
         .addClass("active"));
    });

    //
    // Cache AssignmentComments to local storage
    //


});
