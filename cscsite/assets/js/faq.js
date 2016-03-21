(function ($) {
    "use strict";

    var faq = $("#questions");

    var fn = {
        launch: function () {
            fn.toggleBehaviour();
        },

        toggleBehaviour: function() {
            faq.find('.panel').each(function() {
                $(this).find('.panel-title').attr("aria-expanded", false);
                $(this).find('.panel-collapse').attr("aria-expanded", false).addClass('collapse');
            });
            faq.on('click', '.panel-title', function(e) {
                e.preventDefault();
                var open = $(this).attr("aria-expanded") == "true";
                $(this).attr("aria-expanded", !open);
                $(this).parent().next().toggleClass('collapse').attr("aria-expanded", !open);
            });
        },
    };

    $(document).ready(function () {
        fn.launch();
    });

})(jQuery);