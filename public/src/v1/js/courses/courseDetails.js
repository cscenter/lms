import {getCSRFToken} from "../utils";

export function launch() {
    initTabs();
}

function initTabs() {
    let course = $('#course-detail-page');
    if (course.length > 0) {
        const tabList = $('#course-detail-page__tablist');
        // Switch tabs if url was changed
        window.onpopstate = function (event) {
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
            readCourseNewsOnClick(activeTab.get(0));
        }
        tabList.on('click', 'a', function (e) {
            e.preventDefault();
            if ($(this).parent('li').hasClass('active')) return;

            const targetTab = $(this).data("target");
            if (targetTab === '#course-news') {
                readCourseNewsOnClick(this);
            }
            if (!!(window.history && history.pushState)) {
                history.pushState(
                    {target: targetTab},
                    "",
                    $(this).attr("href")
                );
            }
        });
    }
}


function readCourseNewsOnClick(tab) {
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
}