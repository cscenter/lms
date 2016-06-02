function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

(function ($) {
    "use strict";

    var ends_at_touched = false;

    // map from hash to dummy value (effectively a set)
    var persistedHashes = window.CSCCommentPersistenceHashes;

    // Ubereditors
    var $ubereditors = $("textarea.ubereditor");
    if ($ubereditors.length > 1) {
        console.warn("more than one Ubereditor on page, " +
                     "text restoration may be buggy");
    }

    var $ubertexts = $("div.ubertext");

    // Used to reflow editor on tab toggle event
    var editors = [];

    var MATHJAX_SRC = "//cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML";

    $(document).ready(function () {
        fn.configureCSRFAjax();
        fn.loadMathJaxAndHightlightJS();
        fn.initUberEditor();
        fn.profileSpecificCode();
        fn.courseClassSpecificCode();
        fn.admissionFormSpecificCode();
        // Depends on `editors` var, which populated in initUberEditor method
        fn.reflowEditorOnTabToggle();
        // Note: Not sure, but call it after `initUberEditor` method
        fn.clearEditorsFiles();
    });

    var fn = {
        configureCSRFAjax: function () {
            // Append csrf token on ajax POST requests
            var token = $.cookie('csrftoken');
            $.ajaxSetup({
                beforeSend: function (xhr, settings) {
                    if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                        xhr.setRequestHeader("X-CSRFToken", token);
                    }
                }
            });
        },

        loadMathJaxAndHightlightJS: function () {
            // Note: MathJax and hljs loads for each iframe separately
            if ($ubertexts.length > 0) {
                var scripts = [MATHJAX_SRC, HIGHLIGHTJS_SRC],
                    deferred = $.Deferred(),
                    chained = deferred;
                $.each(scripts, function(i, url) {
                     chained = chained.then(function() {
                         return $.ajax({
                             url: url,
                             dataType: "script",
                             cache: true,
                         });
                     });
                });
                chained.done(function() {
                    fn.configureHighlightJS();
                    fn.initMathJaxAndHightlightJS();
                });
                deferred.resolve();
            }
        },

        configureHighlightJS: function () {
            hljs.configure({tabReplace: '    '});
        },

        initMathJaxAndHightlightJS: function () {
            $ubertexts.each(function (i, target) {
                MathJax.Hub.Queue(["Typeset", MathJax.Hub, target, function () {
                    var $target = $(target);
                    $target.find("pre").addClass("hljs").find('code').each(function (i, block) {
                        // Some teachers uses escape entities inside code block
                        // To prevent &amp;lt; instead of "&lt;", lets double
                        // unescape (&amp; first, then &lt;) and escape again
                        // Note: It can be unpredictable if you want show "&amp;lt;"
                        var t = block.innerHTML;
                        block.innerHTML = _.escape(_.unescape(_.unescape(t)));
                        hljs.highlightBlock(block);
                    });
                }]);
            });
        },

        initUberEditor: function () {
            $ubereditors.each(function (i, textarea) {
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
                }

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

                editor.on('preview', function () {
                    var contentDocument
                        = editor.getElement('previewerIframe').contentDocument;
                    var target = $("#epiceditor-preview", contentDocument).get(0);

                    var text = _.unescape(target.innerHTML);
                    if (text.length > 0) {
                        $.ajax({
                            method: "POST",
                            url: "/tools/markdown/preview/",
                            traditional: true,
                            data: {text: text},
                            dataType: "json"
                        })
                            .done(function (data) {
                                if (data.status == 'OK') {
                                    $(target).html(data.text);
                                    MathJax.Hub.Queue(["Typeset", MathJax.Hub, target, function () {
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
                                }
                            }).error(function (data) {
                            var text;
                            if (data.status == 403) {
                                // csrf token wrong?
                                text = 'Action forbidden';
                            } else {
                                text = "Unknown error. Please, save results of your work first, then try to reload page.";
                            }
                            swal({
                                title: "Error",
                                text: text,
                                type: "error"
                            });
                        });

                    }

                });

                // How often people use this button?
                editor.on('fullscreenenter', function () {
                    if (yaCounter25844420 !== undefined) {
                        yaCounter25844420.reachGoal('MARKDOWN_PREVIEW_FULLSCREEN');
                    }
                });

                editor.on('edit', function () {
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
                    editorBody.addEventListener('keydown', function (e) {
                        if (e.keyCode == 13 && (e.metaKey || e.ctrlKey)) {
                            $textarea[0].form.submit();
                        }
                    });
                }

                editors.push(editor);
            });
        },

        clearEditorsFiles: function () {
            // eliminate old and persisted epiceditor "files"
            if ($ubereditors.length > 0 && window.hasOwnProperty("localStorage")) {
                var editor = new EpicEditor();
                var files = editor.getFiles(null, true);
                _.each(files, function (meta, filename, m) {
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
            }
        },

        profileSpecificCode: function () {
            // TODO: move
            // User info page
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
        },

        courseClassSpecificCode: function() {
            // TODO: Move to appropriate place
            // Course class editing

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
        },

        admissionFormSpecificCode: function() {
            // TODO: Move
            if ($(".forms-iframe").length > 0) {
                $(window).on("message", function(a){
                    var e=a.originalEvent,i=e.data,n=e.source;
                    try{i=JSON.parse(i)}catch(a){}("ping"===i||"ping"===i.message)&&n.postMessage("pong","*")
                });
                $(window).on("message",function(a){
                    var e=a.originalEvent,i=e.data;
                    try{i=JSON.parse(i)}catch(a){}i&&i["iframe-height"]&&$(".forms-iframe").css("height",i["iframe-height"])
                });
            }
        },

        reflowEditorOnTabToggle: function () {
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
        }
    };
})(jQuery, HIGHLIGHTJS_SRC);