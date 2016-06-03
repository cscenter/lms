(function ($) {
    "use strict";

    var fn = {
        launch: function () {
            $('.gallery a').magnificPopup({
                type:'image',
                image: {
                    titleSrc: function(item) {
                        return item.el.attr('title');
                    }
                },
                gallery: {
                    enabled: true,
                    tCounter: '<span class="mfp-counter">%curr% из %total%</span>'
                },
                disableOn: 400,
                key: 'teacher-gallery',
            });
        },
    };

    $(document).ready(function () {
        fn.launch();
    });

})(jQuery);