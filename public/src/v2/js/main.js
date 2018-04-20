import Raven from 'raven-js';
import $ from 'jquery';
import 'bootstrap/js/src/collapse';
import 'bootstrap/js/src/dropdown';

import ravenOptions from './raven_conf';

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
    // Click on `Show programs'
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
});