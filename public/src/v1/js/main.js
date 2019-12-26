import 'bootstrap-sass';
import $ from 'jquery';
import "jgrowl/jquery.jgrowl.js";
// Sentry needs Object.assign
import "core-js/modules/es.object.assign";
import * as Sentry from '@sentry/browser';

import "mathjax_config";
import UberEditor from "./editor";
import {csrfSafeMethod, getCSRFToken, showComponentError} from './utils';
import courseOfferingsList from './main/course_offerings';
import sentryOptions from "./sentry_conf";

// Configure Sentry SDK
Sentry.init({
    dsn: "https://f2a254aefeae4aeaa09657771205672f@sentry.io/13763",
    ...sentryOptions
});


const userInfo = document.getElementById('login');
if (userInfo) {
    let uid = parseInt(userInfo.getAttribute('data-user-id'));
    if (!isNaN(uid)) {
        Sentry.configureScope(scope => {
            scope.setUser({id: uid});
        });
    }
}

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
    fn.courseOfferingTabs();
    // TODO: make it generic with `webpack-entry-module` script attribute
    // Now it checks `id` attr existence in each peace of code ;<
    courseOfferingsList();
    fn.syllabusTabs();

    // FIXME: init chunks (comma separated) instead of sections?
    const section = $("body").data("init-section");
    if (section === "lazy-img") {
        import(/* webpackChunkName: "lazyload" */ 'components/lazyload')
            .then(m => {
                const component = m.default;
                component.launch();
            })
            .catch(error => showComponentError(error));
    }
});

const fn = {
    configureCSRFAjax: function () {
        // Append csrf token on ajax POST requests made with jQuery
        // FIXME: add support for allowed subdomains
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
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
        let course = $('#course-detail-page');
        if (course.length > 0) {
            const tabList = $('#course-detail-page__tablist');
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
                fn.readCourseNewsOnClick(activeTab.get(0));
            }
            tabList.on('click', 'a', function(e) {
                e.preventDefault();
                if ($(this).parent('li').hasClass('active')) return;

                const targetTab = $(this).data("target");
                if (targetTab === '#course-news') {
                    fn.readCourseNewsOnClick(this);
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

    readCourseNewsOnClick: function (tab) {
        let $tab = $(tab);
        if ($tab.data('has-unread')) {
            $.ajax({
                url: $tab.data('notifications-url'),
                method: "POST",
                // Avoiding preflight request by sending csrf token in payload
                data: {"csrfmiddlewaretoken": getCSRFToken()},
                xhrFields: {
                    withCredentials: true
                }
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
                const string_time = $(this).val();
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

    syllabusTabs: function () {
        $('#syllabus-page').on('click', '.nav-tabs a', function(e) {
            e.preventDefault();
            $(this).tab('show');
        });
        $(' ')
    },
};
