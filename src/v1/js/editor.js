import $ from "jquery";
import md5 from "blueimp-md5";
import SweetAlert from "bootstrap-sweetalert";
import {getLocalStorageKey} from "./utils";

import _escape from "lodash-es/escape";
import _unescape from "lodash-es/unescape";

import './EpicEditor';

export default class UberEditor {
    static init(textarea) {
        const $textarea = $(textarea);
        const $container = $("<div/>").insertAfter($textarea);
        const autoSaveEnabled = $textarea.data("local-persist") === true;
        let buttonFullscreen = true;
        if ($textarea.data("button-fullscreen") !== undefined) {
            buttonFullscreen = $textarea.data("button-fullscreen");
        }
        const showHelpFormatting = $textarea.data("helper-formatting") === true;
        $textarea.hide();
        $textarea.removeProp("required");
        // Try to hide help text with formatting helper
        if (showHelpFormatting && $textarea.attr('id')) {
            $(`#hint_${$textarea.attr('id')}`).hide();
        }
        const shouldFocus = $textarea.prop("autofocus");

        const opts = {
            container: $container[0],
            textarea: textarea,
            parser: function(str) {
                // EpicEditor inserts "parsed" html, later we do request
                // to backend in `preview` callback and inserts really
                // parsed text input.
                // To avoid text blinking between those two actions,
                // lets return empty string from here.
                return "";
            },
            focusOnLoad: shouldFocus,
            basePath: "/static/v1/js/vendor/EpicEditor-v0.2.2",
            clientSideStorage: autoSaveEnabled,
            autogrow: {minHeight: 180},
            button: {
                bar: "show",
                fullscreen: false,
                helpFormatting: showHelpFormatting
            },
            theme: {
                base: '/themes/custom/base.css',
                editor: '/themes/custom/editor.css',
                preview: '/themes/custom/preview.css'
            }
        };

        if (autoSaveEnabled) {
            if (textarea.name === undefined) {
                console.error("Missing attr `name` for textarea. " +
                    "Text restore will be buggy.")
            }
            // Presume textarea name is unique for page!
            let filename = getLocalStorageKey(textarea);
            opts['file'] = {
                name: filename,
                defaultContent: "",
                autoSave: 200
            };
        }
        const editor = new EpicEditor(opts);
        editor.load();

        const previewer = editor.getElement("previewer");
        const previewerIframe = editor.getElement("previewerIframe");
        // Append MathJax Configuration
        const iframe_window = previewerIframe.contentWindow || previewerIframe;
        iframe_window.MathJax = window.MathJax;
        // Append MathJax src file
        const mathjax = previewer.createElement('script');
        mathjax.type = 'text/javascript';
        mathjax.src = window.CSC.config.JS_SRC.MATHJAX;
        previewer.body.appendChild(mathjax);

        const previewerDocument = editor.getElement('previewer');
        const epicEditorUtilBar = editor.iframe.getElementById('epiceditor-utilbar');
        let epicEditorPreview = previewerDocument.getElementById('epiceditor-preview');

        editor.on('preview', function () {
            let text = editor._textareaElement.value;
            if (text.length > 0) {
                $.ajax({
                    method: "POST",
                    url: "/tools/markdown/preview/",
                    traditional: true,
                    data: {text: text},
                    dataType: "json"
                })
                .done(function (data) {
                    if (data.status === 'OK') {
                        epicEditorPreview.innerHTML = data.text;
                        editor.getElement('previewerIframe').contentWindow.MathJax.Hub.Queue(function () {
                            editor.getElement('previewerIframe').contentWindow.MathJax.Hub.Typeset(epicEditorPreview, function() {
                                $(epicEditorPreview).find("pre").addClass("hljs");
                                // Note: width reflow breaks full screen
                                editor.emit('__update');
                            });
                        });
                    }
                }).fail(function (data) {
                    let text;
                    if (data.status === 403) {
                        // csrf token wrong?
                        text = 'Action forbidden';
                    } else {
                        text = "Unknown error. Please, save results of your work first, then try to reload page.";
                    }
                    SweetAlert({
                        title: "Error",
                        text: text,
                        type: "error"
                    });
                });
            } else {
                epicEditorPreview.innerHTML = '<i>Нет данных для просмотра</i>';
            }
        });

        // Restore label behavior
        $('label[for=id_' + textarea.name + ']').click(function() {
            editor.focus();
        });
        // Try to fix contenteditable focus problem in Chrome
        $(editor.getElement("editor")).click(function() {
            editor.focus();
        });

        // How often people use this button?
        editor.on('fullscreenenter', function () {
            if (window.yaCounter25844420 !== undefined) {
                window.yaCounter25844420.reachGoal('MARKDOWN_PREVIEW_FULLSCREEN');
            }
        });

        // Ctrl+Enter to send form
        // Submit button value won't be attached to form data, be aware
        // if your form process logic depends on prefix, for example
        if ($textarea[0].getAttribute('data-quicksend') === 'true') {
            let editorBody = editor.getElement('editor').body;
            // FIXME: use .on here
            editorBody.addEventListener('keydown', function (e) {
                if (e.keyCode === 13 && (e.metaKey || e.ctrlKey)) {
                    $textarea.closest("form").submit();
                }
            });
        }
        return editor;
    }

    // FIXME: make it callable once!
    static preload(callback = function() {}) {
        // Stop automatic processing
        $("body").addClass("tex2jax_ignore");
        const scripts = [CSC.config.JS_SRC.MATHJAX,
                         CSC.config.JS_SRC.HIGHLIGHTJS];
        const deferred = $.Deferred();
        let chained = deferred;
        $.each(scripts, function(i, url) {
             chained = chained.then(function() {
                 return $.ajax({
                     url: url,
                     dataType: "script",
                     cache: true,
                 });
             });
        });
        chained.done(callback);
        deferred.resolve();
    }

    static render(target) {
        MathJax.Hub.Queue(["Typeset", MathJax.Hub, target, function () {
            $(target)
                .find("pre").addClass("hljs")
                .find('code').each(function (i, block) {
                // Some teachers use escape entities inside code block
                // To prevent &amp;lt; instead of "&lt;", lets double
                // unescape (&amp; first, then &lt;) and escape again
                // Note: It can be unpredictable if you want show "&amp;lt;"
                const t = block.innerHTML;
                block.innerHTML = _escape(_unescape(_unescape(t)));
                hljs.highlightBlock(block);
            });
        }]);
    }

    static reflowOnTabToggle (e) {
        const activeTab = $($(e.target).attr('href'));
        const editorIframes = activeTab.find('iframe[id^=epiceditor-]');
        let editorIDs = [];
        editorIframes.each(function(i, iframe) {
            editorIDs.push($(iframe).attr('id'));
        });
        $(CSC.config.uberEditors).each(function(i, editor) {
            if ($.inArray(editor._instanceId, editorIDs) !== -1) {
                editor.emit('__update');
            }
        });
    }

    static cleanLocalStorage (ubereditors) {
        // eliminate old and persisted epiceditor "files"
        if (ubereditors.length > 0 && window.hasOwnProperty("localStorage")) {
            const editor = new EpicEditor();
            const files = editor.getFiles(null, true);
            Object.keys(files).forEach((fileKey) => {
                let f = files[fileKey];
                const hoursOld = (((new Date()) - (new Date(f.modified))) / (1000 * 60 * 60));
                if (hoursOld > 24) {
                    editor.remove(fileKey);
                } else if (CSC.config.localStorage.hashes) {
                    let text = editor.exportFile(fileKey).replace(/\s+/g, '');
                    let hash = md5(text).toString();
                    if (hash in CSC.config.localStorage.hashes) {
                        editor.remove(fileKey);
                    }
                }
            });
        }
    }
}
