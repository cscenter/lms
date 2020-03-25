// FIXME: polyfill for classList? https://www.npmjs.com/package/classlist-polyfill
// FIXME:  https://babeljs.io/docs/en/next/babel-plugin-syntax-dynamic-import#working-with-webpack-and-babel-preset-env
import 'core-js/modules/es.array.iterator';
import "core-js/modules/es.promise";
// Sentry needs Object.assign
import "core-js/modules/es.object.assign";
import * as Sentry from '@sentry/browser';
import 'bootstrap.native';
import ky from 'ky';

import sentryOptions from './sentry_conf';
import {
    onReady,
    loadFetchPolyfill,
    polyfillElementMatches,
    showComponentError,
    getSections,
    showNotification,
    showErrorNotification
} from 'utils';

// Configure Sentry SDK
Sentry.init({
    dsn: process.env.SENTRY_DSN,
    ...sentryOptions
});
const userInfo = document.getElementById('userMenuButton');
if (userInfo) {
    let uid = parseInt(userInfo.getAttribute('data-id'));
    if (!isNaN(uid)) {
        Sentry.configureScope(scope => {
            scope.setUser({id: uid});
        });
    }
}


onReady(async () => {
    initTopMenu();
    displayNotifications();
    // Global polyfills
    await Promise.all([loadFetchPolyfill(), polyfillElementMatches()]);

    // TODO: section or component-based approach. What to choose?
    let sections = getSections();
    if (sections.includes("honorBoard")) {
        import(/* webpackChunkName: "honorBoard" */ 'apps/honorBoard')
            .then(module => { module.launch(); })
            .catch(error => showComponentError(error));
    }
    if (sections.includes("surveys")) {
        import(/* webpackChunkName: "surveys" */ 'apps/surveys')
            .then(module => { module.launch(); })
            .catch(error => showComponentError(error));
    }
    if (sections.includes("collapsible")) {
        import(/* webpackChunkName: "collapsible" */ 'apps/collapsible')
            .then(module => { module.launch(); })
            .catch(error => showComponentError(error));
    }
    if (sections.includes("scrollspy")) {
        import(/* webpackChunkName: "scrollspy" */ 'apps/scrollspy')
            .then(module => { module.launch(); })
            .catch(error => showComponentError(error));
    }
    if (sections.includes("tabs")) {
        import(/* webpackChunkName: "tabs" */ 'apps/tabs')
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

    loadSVGSprites();
    loadLazyImages();
    renderLatex();
});

function initTopMenu() {
    let navbarContainer = document.querySelector(".navbar-container");
    let navbarToggler = document.querySelector(".navbar-toggler");
    let menuRightBlock = document.querySelector(".dropdown-user-menu") ||
                         document.querySelector(".menu-btn-reg");
    const topMenu = document.querySelector('#top-menu-mobile');
    if (topMenu) {
        topMenu.addEventListener('show.bs.collapse', function (event) {
            // Ignores bubbled events from submenu
            if (event.target.classList.contains("mobile-submenu")) {
                return;
            }
            document.body.style.height = "100%";
            document.body.style.overflow = "hidden";
            navbarContainer.style.height = "100%";
            navbarContainer.style.overflowY = "scroll";
            navbarToggler.classList.add("is-active");
            menuRightBlock.style.display = "none";
        });
        topMenu.addEventListener('hide.bs.collapse', function (event) {
            // Ignores bubbled events from submenu
            if (event.target.classList.contains("mobile-submenu")) {
                return;
            }
            navbarToggler.classList.remove("is-active");
            menuRightBlock.style.removeProperty("display");
        });
        topMenu.addEventListener('hidden.bs.collapse', function (event) {
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
    }
}

function displayNotifications() {
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
}

function loadSVGSprites() {
    window.__CSC__.sprites.forEach((url) => {
        ky.get(url)
            .then((response) => response.text())
            .then((svgDefs) => {
                document.querySelector(".svg-inline")
                        .insertAdjacentHTML('beforeend', svgDefs);
            });
    });
}

// Replaces `data-src` attribute
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

function renderLatex() {
    const katexBlocks = document.getElementsByClassName('math-support');
    if (katexBlocks.length > 0) {
        import(/* webpackChunkName: "katex" */ 'katex/dist/katex.css');
        import(/* webpackChunkName: "katex" */ 'katex_renderer')
            .then(module => {
                katexBlocks.forEach(function(mathBlock) {
                    module.renderMath(mathBlock);
                });
            })
            .catch(error => showComponentError(error));
    }
}
