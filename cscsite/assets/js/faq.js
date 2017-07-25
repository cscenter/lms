(function ($) {
    "use strict";

    var faq = $("#questions-wrapper");

    var fn = {
        launch: function () {
            fn.toggleBehaviour();
        },

        toggleBehaviour: function() {
            // Replace js animation with css.
            faq.on('click', '.panel-title', function(e) {
                e.preventDefault();
                var open = $(this).attr("aria-expanded") === "true";
                $(this).parent().next().toggleClass('collapse').attr("aria-expanded", !open);
                $(this).attr("aria-expanded", !open);
            });
        },
    };

    $(document).ready(function () {
        fn.launch();
    });

})(jQuery);