// FIXME: can't replace tab module with bootstrap.native and remove jquery from here right now since it doesn't respect `data-target` over `href` value.
import $ from 'jquery';
import 'bootstrap/js/src/tab';
import { toEnhancedHTMLElement } from "@drivy/dom-query"


function toggleTab(event) {
    // Replace js animation with css.
    event.preventDefault();
    $(this).tab('show');
}

export function launch() {
    document.getElementsByClassName('nav-tabs').forEach(function(item) {
        const tabList = toEnhancedHTMLElement(item);
        // Selected tab on page loading
        let defaultTab = tabList.query('.nav-item .active[data-toggle="tab"]');
        if (defaultTab === null) {
            defaultTab = tabList.query('.nav-item [data-toggle="tab"]');
        }
        console.debug(`tabs: active tab on page loading: ${defaultTab}`);
        if (defaultTab === null) {
            return;
        }
        if (tabList.classList.contains('browser-history')) {
            // Toggle tab if the url has changed
           window.onpopstate = function (event) {
               let tabTarget;
               if (event.state !== null) {
                   if ('tabTarget' in event.state) {
                       tabTarget = event.state.tabTarget;
                   }
               }
               if (tabTarget === undefined) {
                   tabTarget = defaultTab.getAttribute('data-target');
               }
               $(item)
                   .find('.nav-link[data-target="' + tabTarget + '"]')
                   .tab('show');
           };

            tabList.onDelegate('[data-toggle="tab"]', 'click', function (event) {
                toggleTab(event);
                if (!!(window.history && history.pushState)) {
                    history.pushState(
                        {tabTarget: this.getAttribute("data-target")},
                        "",
                        this.getAttribute("href")
                    );
                }
            });
       } else {
            tabList.onDelegate('[data-toggle="tab"]', 'click', toggleTab);
       }
    });
}