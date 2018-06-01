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
});
if (authenticatedUser !== undefined && !isNaN(parseInt(authenticatedUser))) {
    Raven.setUserContext({
        id: authenticatedUser
    });

}
