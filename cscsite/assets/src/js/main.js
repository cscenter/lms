import Cookies from 'js-cookie';
import 'bootstrap-sass';
import $ from 'jquery';
import md5 from "blueimp-md5";
import "jgrowl/jquery.jgrowl.js";
import swal from "bootstrap-sweetalert";
import "mathjax_config";
import UberEditor from "./editor";
import {csrfSafeMethod} from './utils';

const CSC = window.CSC;


// Replace textarea with EpicEditor
const $ubereditors = $("textarea.ubereditor");

// Process highlight js and MathJax
const $ubertexts = $("div.ubertext");

let ends_at_touched = false;

$(document).ready(function () {
    fn.configureCSRFAjax();
    fn.renderText();
    // Clean stale local storage cache
    fn.cleanLocalStorageEditorsFiles();
    fn.initUberEditors();
    fn.courseClassSpecificCode();
    fn.admissionFormSpecificCode();
    // Depends on `editors` var, which populated in initUberEditor method
    fn.reflowEditorOnTabToggle();
});

const fn = {
    configureCSRFAjax: function () {
        // Append csrf token on ajax POST requests made with jQuery
        const token = Cookies.get('csrftoken');
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", token);
                }
            }
        });
    },

    renderText: function () {
        // Note: MathJax and hljs loads for each iframe separately
        if ($ubertexts.length > 0) {
            UberEditor.preload(function () {
                // Configure highlight js
                hljs.configure({tabReplace: '    '});
                // Render Latex and highlight code
                $ubertexts.each(function (i, target) {
                    UberEditor.render(target);
                });
            });
        }
    },

    initUberEditors: function () {
        $ubereditors.each(function (i, textarea) {
            const editor = UberEditor.init(textarea);
            CSC.config.uberEditors.push(editor);
        });
    },
    // TODO: move logic to new editor module
    cleanLocalStorageEditorsFiles: function () {
        // eliminate old and persisted epiceditor "files"
        if ($ubereditors.length > 0 && window.hasOwnProperty("localStorage")) {
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
    },
    // TODO: move logic to new editor module
    reflowEditorOnTabToggle: function () {
        $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
            var activeTab = $($(e.target).attr('href'));
            var editorIframes = activeTab.find('iframe[id^=epiceditor-]');
            var editorIDs = [];
            editorIframes.each(function(i, iframe) {
                editorIDs.push($(iframe).attr('id'));
            });
            $(CSC.config.uberEditors).each(function(i, editor) {
                if ($.inArray(editor._instanceId, editorIDs) !== -1) {
                    editor.reflow();
                }
            });
        });
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
    }
};
