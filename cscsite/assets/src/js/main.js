import Cookies from 'js-cookie';
import 'bootstrap-sass';
import $ from 'jquery';
import "jgrowl/jquery.jgrowl.js";
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
    fn.initUberEditors();
    fn.courseClassSpecificCode();
    fn.applicationForm();
    fn.courseOfferingTabs();
    fn.syllabusTabs();
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
        UberEditor.cleanLocalStorage($ubereditors);
        $ubereditors.each(function (i, textarea) {
            const editor = UberEditor.init(textarea);
            CSC.config.uberEditors.push(editor);
        });
        if ($ubereditors.length > 0) {
            $('a[data-toggle="tab"]').on('shown.bs.tab',
                                         UberEditor.reflowOnTabToggle);
        }
    },

    courseOfferingTabs: function() {
        let course_offering = $('#course-offering-detail-page').data('id');
        if (course_offering !== undefined) {
            const tabList = $('#course-offering-detail-page__tablist');
            // Switch tabs if url was changed
            window.onpopstate = function(event) {
                let target;
                if (event.state !== null) {
                    if ('target' in event.state) {
                        target = event.state.target;
                    }
                }
                if (target === undefined) {
                    if (window.location.hash.indexOf("#news-") !== -1) {
                        target = "#course-news";
                    } else {
                        target = "#course-about";
                    }
                }
                tabList.find('li').removeClass('active').find('a').blur();
                tabList.find('a[data-target="' + target + '"]').tab('show').hover();
            };
            let activeTab = tabList.find('li.active:first a:first');
            if (activeTab.data("target") === '#course-news') {
                fn.markNewsAsRead(course_offering, activeTab.get(0));
            }
            tabList.on('click', 'a', function(e) {
                e.preventDefault();
                if ($(this).parent('li').hasClass('active')) return;

                const targetTab = $(this).data("target");
                if (targetTab === '#course-news') {
                    fn.markNewsAsRead(course_offering, this);
                }
                if (!!(window.history && history.pushState)) {
                    history.pushState(
                        {target:targetTab},
                        "",
                        $(this).attr("href")
                    );
                }
            });
        }
    },

    markNewsAsRead: function (course_offering, tab) {
        let $tab = $(tab);
        if ($tab.data('has-unread')) {
            $.ajax({
                // TODO: Pass url in data attr?
                url: "/notifications/course-offerings/news/",
                method: "POST",
                data: {co: course_offering}
            }).done((data) => {
                if (data.updated) {
                    $tab.text(tab.firstChild.nodeValue.trim());
                }
                // Prevent additional requests
                $tab.data("has-unread", false);
            });
        }
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

    applicationForm: function() {
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

    syllabusTabs: function () {
        $('#syllabus-page').on('click', '.nav-tabs a', function(e) {
            e.preventDefault();
            $(this).tab('show');
        });
        $(' ')
    }
};
