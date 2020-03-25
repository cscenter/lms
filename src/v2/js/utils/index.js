import Noty from 'noty';


export const onReady = function( callback ) {
	if (document.readyState === 'complete' || document.readyState === 'interactive') {
		return callback();
	}

	document.addEventListener( 'DOMContentLoaded', callback );
};

// TODO: move polyfills to the `polyfills/index.js`
// TODO: load all polyfills in 1 request

/**
 * For browsers that do not support Element.matches() or Element.matchesSelector(), but include
 * support for document.querySelectorAll(). IE9+ version
 */
export function polyfillElementMatches() {
    if (!Element.prototype.matches) {
      Element.prototype.matches = Element.prototype.msMatchesSelector ||
                                  Element.prototype.webkitMatchesSelector;
    }
}

/**
 * Polyfill fetch API for browsers without native support.
 **/
export function loadFetchPolyfill() {
    if (typeof window === 'object' && (!window.fetch || !window.AbortController)) {
        return import(/* webpackChunkName: "fetch-polyfill" */ 'polyfills/fetch');
    }
}


/**
 * Do feature detection, to figure out if polyfill needs to be imported.
 **/
export async function loadIntersectionObserverPolyfill() {
    if (typeof window.IntersectionObserver === 'undefined') {
        return import(/* webpackChunkName: "intersection-observer" */ 'intersection-observer');
    }
}

export function getSections() {
    if (document.body.hasAttribute("data-init-sections")) {
        let sections = document.body.getAttribute("data-init-sections");
        return sections.split(",");
    } else {
        return [];
    }
}

export function showComponentError(error, msg = 'An error occurred while loading the component') {
    showErrorNotification(msg);
    console.error(error);
}

export function showNotification(msg, options) {
    new Noty({
        layout: 'bottomRight',
        type: 'info',
        theme: 'notification',
        text: msg,
        timeout: 2000,
        animation: {
            close: 'noty_effects_close'
        },
        ...options
    }).show();
}

export function showErrorNotification(msg) {
    showNotification(msg, {
        type: "error",
        timeout: false,
        closeWith: ['button']
    });
}

export function showBodyPreloader() {
    document.body.classList.add("_fullscreen");
    document.body.classList.add("_loading");
}

export function hideBodyPreloader() {
    document.body.classList.remove("_fullscreen");
    document.body.classList.remove("_loading");
}
