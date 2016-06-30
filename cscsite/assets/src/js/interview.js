(function ($) {
    "use strict";

    var ratingSelect = $("select#id_score");

    var commentForm = $("#comment form");

    var commentTextarea = $("textarea[name=text]", commentForm);

    var fn = {
        launch: function () {
            fn.initRatingBar();
            fn.submitFormHandler();

            // Restore tab
            var hash = window.location.hash;
            hash && $('ul.nav a[href="' + hash + '"]').tab('show');

            $('.nav-tabs a').click(function (e) {
                $(this).tab('show');
                var scrollmem = $('body').scrollTop() || $('html').scrollTop();
                $('html,body').scrollTop(scrollmem);
            });
        },

        initRatingBar: function() {
            ratingSelect.barrating({
                theme: 'bars-movie',
                hoverState: false
            });
        },

        submitFormHandler: function () {
            // Stupid defense from stale sessions
            commentForm.submit(function (e) {
                e.preventDefault();
                var _data = commentForm.serializeArray();
                var data= {};
                $.map(_data, function(n, i){
                    data[n['name']] = n['value'];
                });
                $.ajax({
                    url: commentForm.attr("action"),
                    data: JSON.stringify(data),
                    dataType: 'json',
                    type: 'POST',
                }).done(function (data) {
                    // Form was valid and saved, reload the page
                    if (data.success == "true") {
                        $.jGrowl(
                            "Комментарий успешно сохранён",
                            { position: 'bottom-right' }
                        );
                        // FIXME: update #comments block instead of reload!
                        setTimeout(function () {
                            window.location.reload();
                        }, 500);
                    } else {
                        swal({
                            title: "Ошибка валидации",
                            text: "Укажите оценку перед сохранением.",
                            type: "warning",
                            confirmButtonText: "Хорошо"
                        });
                    }
                }).fail(function (data) {
                    swal({
                        title: "Всё плохо!",
                        text: "Пожалуйста, скопируйте результаты своей работы и попробуйте перезагрузить страницу.",
                        type: "error"
                    });
                });
            })
        }
    };

    $(document).ready(function () {
        fn.launch();
    });

})(jQuery);