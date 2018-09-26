import Raven from 'raven-js';
import $ from 'jquery';
import '@babel/polyfill';
import 'bootstrap/js/src/collapse';
import 'bootstrap/js/src/dropdown';

import ravenOptions from './raven_conf';
import {
    showComponentError,
    getSections,
    showNotification,
    showErrorNotification
} from 'utils';

// Configure `raven-js`
Raven
    .config('https://8e585e0a766b4a8786870813ed7a4be4@app.getsentry.com/13763',
            ravenOptions)
    .install();
let authenticatedUser = $("#userMenuButton").data('id');
if (authenticatedUser !== undefined && !isNaN(parseInt(authenticatedUser))) {
    Raven.setUserContext({
        id: authenticatedUser
    });
}

$(function () {
    let navbarContainer = document.getElementsByClassName("navbar-container")[0];
    let navbarToggler = $(".navbar-toggler");
    let menuRightBlock = document.getElementsByClassName("dropdown-user-menu")[0] ||
                         document.getElementsByClassName("menu-btn-reg")[0];
    $('#top-menu-mobile')
        .on('show.bs.collapse', function (event) {
            // Ignores bubbled events from submenu
            if (event.target.classList.contains("mobile-submenu")) {
                return;
            }
            document.body.style.height = "100%";
            document.body.style.overflow = "hidden";
            navbarContainer.style.height = "100%";
            navbarContainer.style.overflowY = "scroll";
            navbarToggler.addClass("is-active");
            menuRightBlock.style.display = "none";
        })
        .on('hide.bs.collapse', function (event) {
            // Ignores bubbled events from submenu
            if (event.target.classList.contains("mobile-submenu")) {
                return;
            }
            navbarToggler.removeClass("is-active");
            menuRightBlock.style.removeProperty("display");
        })
        .on('hidden.bs.collapse', function (event) {
            // Ignores bubbled events from submenu
            if (event.target.classList.contains("mobile-submenu")) {
                return;
            }
            navbarContainer.style.height = "";
            navbarContainer.style.overflowY = "visible";
            document.getElementsByClassName("navbar-container")[0].style.height = "";
            document.body.style.height = "";
            document.body.style.overflow = "auto";
        });

    // Click `Show Programs' on index page
    $('a[href="#offline-courses"]').click(function (e) {
        e.preventDefault();
        let scrollTo = $(this).attr('href');
        // Adjustment for top navbar height on small screens
        let offset = parseInt($('.cover').css('padding-top'), 10);
        if (offset > 0) {
            offset = $('.navbar-container').outerHeight(true);
        }
        $('html, body').animate({
            scrollTop: $(scrollTo).offset().top - offset
        }, 700);
    });

    // Notifications
    if (window.__CSC__.notifications !== undefined) {
        window.__CSC__.notifications.forEach((item) => {
            const {text, ...props} = item;
            if (props.type === "error") {
                showErrorNotification(text, props);
            } else {
                showNotification(text, props);
            }
        });
    }

    // TODO: section or component-based approach. What to choose?
    let sections = getSections();
    if (sections.includes("honorBoard")) {
        import(/* webpackChunkName: "honorBoard" */ 'apps/honorBoard')
            .then(module => { module.launch(); })
            .catch(error => showComponentError(error));
    }

    let reactApps = document.querySelectorAll('.__react-root');
    if (reactApps.length > 0) {
        import(/* webpackChunkName: "react" */ 'react_app')
            .then(m => {
                Array.from(reactApps).forEach(m.renderComponentInElement);
            })
            .catch(error => showComponentError(error));
    }

    // Append svg sprites
    window.__CSC__.sprites.forEach((url) => {
        $.ajax({
            type: "GET",
            url: url,
            dataType: "text",
        }).then((svgDefs) => {
            $(".svg-inline").append(svgDefs);
        });
    });

    // Replace data-src
    loadLazyImages();
});


function loadLazyImages() {
    const attribute = 'data-src';
    const matches = document.querySelectorAll('img[' + attribute + ']');
    if (matches.length > 0) {
        let srcsetIsSupported = "srcset" in matches[0];
        for (let i = 0, n = matches.length; i < n; i++) {
            if (srcsetIsSupported) {
                let srcset = matches[i].getAttribute("data-srcset");
                if (srcset !== null) {
                    matches[i].setAttribute('srcset', srcset);
                }
            }
            // Fallback to src
            matches[i].setAttribute('src', matches[i].getAttribute(attribute));
        }

    }
}
