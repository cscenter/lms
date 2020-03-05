import {toEnhancedHTMLElement} from "@drivy/dom-query";
import Tab from 'bootstrap5/tab';


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
            for (const tab of tabList.queryAll('[data-toggle="tab"]')) {
                new Tab(tab);
            }
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
               let tabLink = tabList.query('[data-target="' + tabTarget + '"]');
               Tab.getInstance(tabLink).show();
           };

            tabList.onDelegate('[data-toggle="tab"]', 'click', function (event) {
                if (window.history && history.pushState) {
                    history.pushState(
                        {tabTarget: this.getAttribute("data-target")},
                        "",
                        this.getAttribute("href")
                    );
                }
            });
       }
    });
}