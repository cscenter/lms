(function ($) {
    "use strict";

    var fn = {
        launch: function () {
            $("img.lazy").lazyload({
            });
        },
    };

    $(document).ready(function () {
        fn.launch();
    });

})(jQuery);