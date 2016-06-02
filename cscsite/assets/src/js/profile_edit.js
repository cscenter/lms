(function ($) {
    "use strict";

    var fn = {
        launch: function () {
            $('#id_phone').inputmask({
              mask: '+8-(999)-999-99-99'
            });
        },
    };

    $(document).ready(function () {
        fn.launch();
    });

})(jQuery);