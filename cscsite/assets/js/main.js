"use strict";

var ends_at_touched = false;
var marks_sheet_unsaved = 0;

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$(document).ready(function () {

    $('#id_phone').inputmask({
      mask: '+8-(999)-999-99-99'
    })


    var csrftoken = $.cookie('csrftoken');
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    //
    // State
    //

    // map from hash to dummy value (effectively a set)
    var persistedHashes = window.CSCCommentPersistenceHashes;

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
                ? hljs.highlight(lang, unescaped, true).value
                : unescaped;
        },
        smartypants: false,
        langPrefix: 'language-',
    });

    $("div.ubertext").each(function(i, target) {

        MathJax.Hub.Queue(["Typeset", MathJax.Hub, target, function() {
            var $target = $(target);
            $target.find("pre").addClass("hljs").each(function(i, block) {
                hljs.highlightBlock(block);
            });
        }]);
    });

    //
    // Ubereditors
    //

    var $ubereditors = $("textarea.ubereditor");
    if ($ubereditors.length > 1) {
        console.warn("more than one Ubereditor on page, " +
                     "text restoration may be buggy");
    }

    // eliminate old and persisted epiceditor "files"
    if ($ubereditors.length > 0 && window.hasOwnProperty("localStorage")) {
        (function() {
            var editor = new EpicEditor();
            var files = editor.getFiles(null, true);
            _.each(files, function(meta, filename, m) {
                var hoursOld = (((new Date()) - (new Date(meta.modified)))
                                / (1000 * 60 * 60));
                if (hoursOld > 24) {
                    editor.remove(filename);
                } else if (persistedHashes) {
                    var text = editor.exportFile(filename).replace(/\s+/g, '');
                    var hash = CryptoJS.MD5(text).toString();
                    if (hash in persistedHashes) {
                        editor.remove(filename);
                    }
                };
            });
        })();
    };

    var editors = [];

    $ubereditors.each(function(i, textarea) {
        var $textarea = $(textarea);
        var $container = $("<div/>").insertAfter($textarea);
        var shouldFocus = false;
        var ubereditorRestoration = $textarea.data('local-persist') == true;

        $textarea.hide();
        shouldFocus = $textarea.prop("autofocus");
        $textarea.removeProp("required");

        var opts = {
            container: $container[0],
            textarea: $textarea[0],
            parser: null,
            focusOnLoad: shouldFocus,
            basePath: "/static/js/vendor/EpicEditor-v0.2.2",
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
                autoSave: 300
            };
        };

        var editor = new EpicEditor(opts);


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
                target.innerHTML = marked(_.unescape(target.innerHTML));
                $(target).find("pre").addClass("hljs");
                if (!editor.is('fullscreen')) {
                    var height = Math.max(
                        $(target).height() + 20,
                        editor.settings.autogrow.minHeight
                    );
                    $container.height(height);
                }
                editor.reflow();
            }]);
        });

        editor.on('edit', function() {
            if (!editor.is('fullscreen')) {
                var height = Math.max(
                    $(editor.getElement('editor').body).height() + 20,
                    editor.settings.autogrow.minHeight
                );
                $container.height(height);
            }
            editor.reflow();
        });

        // Ctrl+Enter to send form
        if ($textarea[0].dataset.quicksend == 'true') {
            var editorBody = editor.getElement('editor').body;
            // FIXME: use .on here
            editorBody.addEventListener('keydown', function(e) {
                if (e.keyCode == 13 && (e.metaKey || e.ctrlKey)) {
                    $textarea[0].form.submit();
                };
            });
        }

        editors.push(editor);
    });


    // Tab toggle events
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        var activeTab = $($(e.target).attr('href'));
        var editorIframes = activeTab.find('iframe[id^=epiceditor-]');
        var editorIDs = [];
        editorIframes.each(function(i, iframe) {
            editorIDs.push($(iframe).attr('id'));
        });
        $(editors).each(function(i, editor) {
            if ($.inArray(editor._instanceId, editorIDs) !== -1) {
                editor.reflow();
            }
        });
    });

    //
    // Course class editing
    //

    // FIXME: use .on here
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
                console.warning("Can't parse " + string_time);
            }
        }
    });

    //
    // User info page
    //

    (function() {
        var $btnGroup = $("div.assignment-list-control");
        var $oldRows = $("#assignments-table .old");

        $btnGroup
            .on("click", ".current-semester", function(e) {
                var $target = $(e.target);
                $btnGroup.find(".all").removeClass("active");
                $target.addClass("active");
                $oldRows.hide();

            })
            .on("click", ".all", function(e) {
                var $target = $(e.target);
                $btnGroup.find(".current-semester").removeClass("active");
                $target.addClass("active");
                $oldRows.show();

            });
    })();


    //
    // Marks sheet (for teacher's one and staff's)
    //

    if (marks_sheet_unsaved == 0) {
        $("#marks-sheet-save").attr("disabled", "disabled");
    }

    $(".marks-table.teacher").on("change", "input,select", function (e) {
        var $this = $(this);
        var $target = $(e.target);
        var $csv_link = $(".marks-sheet-csv-link");
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
    });

    // see this http://stackoverflow.com/a/8641208 for discussion
    // about the following hack
    $('.marks-table').each(function (i) {
        $(this).find('tr').each(function() {
            $(this).find('td').each(function(j) {
                // order marks sheets for different course offerings properly
                var idx = j + 1000 * (i + 1);
                $(this).find('input,select').prop('tabindex', idx);
            });
        });
    });

    $('.marks-table')
    // NOTE(Dmitry): this is needed to prevent default change-on-scroll
    //               behavior on HTML5 number input fields
        .on('mousewheel', 'input[type=number]', function (e) {
            this.blur();
        })
        .on('keypress', 'input', function(e) {
            var code = e.keyCode || e.which;
            if (code == 13 || code == 10) {
                if (e.metaKey || e.ctrlKey) {
                    this.form.submit();
                } else {
                    e.preventDefault();
                    return false;
                }
            }
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

    if ($('.user-search').length > 0) {
        var enrollmentYears = {};
        var qstr = "";
        var ajaxURI = $('.user-search #ajax-uri').val();
        var query = function() {
            var flatYears;

            flatYears = _.chain(enrollmentYears)
                .pairs()
                .filter(function(x) {return x[1]})
                .map(function(x) {return x[0]})
                .value();
            console.log(flatYears);
            $.ajax({
                url: ajaxURI,
                data: {name: qstr,
                       enrollment_years: flatYears},
                dataType: "json",
                traditional: true
            }).done(function(msg) {
                var numStr = (msg.users.length.toString()
                              + (msg.there_is_more ? "+" : ""));

                $("#user-num-container").show();
                $("#user-num").text(numStr);
                var h = "<table class=\"table table-condensed\">";
                _.each(msg.users, function(user) {
                    h += "<tr><td><a href=\"" + user.url  + "\">";
                    h += user.last_name + " " + user.first_name;
                    h += "</a></td></tr>";
                });
                if (msg.there_is_more) {
                    h += "<tr><td>…</td></tr>";
                }
                h += "</table>";
                $("#user-table-container").html(h);
            });
        };
        query = _.debounce(query, 200);

        $('.user-search [name="enrollment_year_cb"]')
            .each(function(idx, obj) {
                enrollmentYears[$(obj).val()] = false;
            });

        $('.user-search')
            .on('input paste', '#name', function (e) {
                qstr = $(this).val();
                query();
            })
            .on('change', '[name="enrollment_year_cb"]', function (e) {
                enrollmentYears[$(this).val()] = this.checked;
                query();
            });

    }

});
