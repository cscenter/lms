import $ from 'jquery';
import 'bootstrap/js/src/collapse';
import 'bootstrap/js/src/dropdown';

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