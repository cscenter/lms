var ravenOptions = {
    // Will cause a deprecation warning, but the demise of `ignoreErrors` is still under discussion.
    // See: https://github.com/getsentry/raven-js/issues/73
    ignoreErrors: [
        // Random plugins/extensions
        'top.GLOBALS',
        // See: http://blog.errorception.com/2012/03/tale-of-unfindable-js-error.html
        'originalCreateNotification',
        'canvas.contentDocument',
        'MyApp_RemoveAllHighlights',
        'http://tt.epicplay.com',
        'Can\'t find variable: ZiteReader',
        'jigsaw is not defined',
        'ComboSearch is not defined',
        'http://loading.retry.widdit.com/',
        'atomicFindClose',
        // Facebook borked
        'fb_xd_fragment',
        // ISP "optimizing" proxy - `Cache-Control: no-transform` seems to reduce this. (thanks @acdha)
        // See http://stackoverflow.com/questions/4113268/how-to-stop-javascript-injection-from-vodafone-proxy
        'bmi_SafeAddOnload',
        'EBCallBackMessageReceived',
        // See http://toolbar.conduit.com/Developer/HtmlAndGadget/Methods/JSInjection.aspx
        'conduitPage',
        // Generic error code from errors outside the security sandbox
        // You can delete this if using raven.js > 1.0, which ignores these automatically.
        'Script error.'
    ],
    ignoreUrls: [
        // Facebook flakiness
            /graph\.facebook\.com/i,
        // Facebook blocked
            /connect\.facebook\.net\/en_US\/all\.js/i,
        // Woopra flakiness
            /eatdifferent\.com\.woopra-ns\.com/i,
            /static\.woopra\.com\/js\/woopra\.js/i,
        // Chrome extensions
            /extensions\//i,
            /^chrome:\/\//i,
        // Other plugins
            /127\.0\.0\.1:4001\/isrunning/i,  // Cacaoweb
            /webappstoolbarba\.texthelp\.com\//i,
            /metrics\.itunes\.apple\.com\.edgesuite\.net\//i,
        // Kaspersky Protection browser extension
            /kaspersky-labs\.com/i
    ]
};
Raven.config('https://8e585e0a766b4a8786870813ed7a4be4@app.getsentry.com/13763', ravenOptions).install();
var $faUser = $("#login").data('user-id');
if (!isNaN(parseInt($faUser))) {
    Raven.setUserContext({
        id: $faUser
    });
}
