import $ from 'jquery';
import 'bootstrap/js/src/tab';

function toggleTab(event) {
    // Replace js animation with css.
    event.preventDefault();
    $(this).tab('show');
}

export function launch() {
    document.getElementsByClassName('nav-tabs').forEach(function(item) {
        const tabList = $(item);
        // Stores tab selected on page loading
        let defaultTab = tabList.find('.nav-link.active');
        if (defaultTab.length !== 1) {
            defaultTab = tabList.find('.nav-link').first();
        }
        console.debug(`tabs: active tab on page loading: ${defaultTab.get(0)}`);
        if (tabList.hasClass('browser-history')) {
            // Toggle tab if the url has changed
           window.onpopstate = function (event) {
               let tabTarget;
               if (event.state !== null) {
                   if ('tabTarget' in event.state) {
                       tabTarget = event.state.tabTarget;
                   }
               }
               if (tabTarget === undefined) {
                   tabTarget = defaultTab.data('target');
               }
               tabList
                   .find('.nav-link[data-target="' + tabTarget + '"]')
                   .tab('show');
           };
           tabList.find('.nav-link').on('click', function (event) {
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
           $(this).find('.nav-link').on('click', toggleTab);
       }
    });
}