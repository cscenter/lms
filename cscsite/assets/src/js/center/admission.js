import UberEditor from "../editor";
import 'jquery-bar-rating';

(function ($) {
    "use strict";

    const assignmentsWrapper = $(".assignments-multicheckbox");
    const assignmentPreviewWrapper = $("#interview-assignment-model-form");
    // Interview page
    const ratingSelect = $("select#id_score");
    const commentForm = $("#comment form");

    var fn = {
        launch: function () {
            fn.assignmentsMultiSelect();

            fn.initRatingBar();
            fn.initInterviewCommentForm();

            // Restore tab
            let hash = window.location.hash;
            hash && $('ul.nav a[href="' + hash + '"]').tab('show');

            $('.nav-tabs a').click(function (e) {
                $(this).tab('show');
                const scrollmem = $('body').scrollTop() || $('html').scrollTop();
                $('html,body').scrollTop(scrollmem);
            });
        },

        assignmentsMultiSelect: function() {
            // Some behavior on `assignments` multiple select
            assignmentsWrapper.on("mouseenter", ".checkbox", function () {
                let span = $(this).find("span");
                span.removeClass("text-muted");
                span.addClass("text-info");
                span.text('Посмотреть условие');
            });
            assignmentsWrapper.on("mouseleave", ".checkbox", function () {
                let span = $(this).find("span");
                span.addClass("text-muted");
                span.removeClass("text-info");
                span.text(span.data('text'));
            });


            const modalBody = $('.modal-body', assignmentPreviewWrapper);
            assignmentPreviewWrapper.modal({
                show: false
            });

            UberEditor.preload();

            assignmentsWrapper.on("click", ".checkbox span", function () {
                // Show modal
                const $this = $(this);
                // TODO: get reverse from js instead of hardcoding each link
                $.get($this.data("href"), function (data) {
                    $('.modal-title', assignmentPreviewWrapper).html(data.name);
                    modalBody.html(data.description);
                    UberEditor.render(modalBody.get(0));
                    assignmentPreviewWrapper.modal('toggle');
                }).error(function (data) {
                });
            });
        },

        initRatingBar: function() {
            ratingSelect.barrating({
                theme: 'bars-movie',
                hoverState: false
            });
        },

        initInterviewCommentForm: function () {
            // Stupid defense from stale sessions
            commentForm.submit(function (e) {
                e.preventDefault();
                const _data = commentForm.serializeArray();
                let data= {};
                $.map(_data, function(n, i) {
                    data[n['name']] = n['value'];
                });
                $.ajax({
                    url: commentForm.attr("action"),
                    data: JSON.stringify(data),
                    dataType: 'json',
                    type: 'POST',
                }).done(function (data) {
                    // Form was valid and saved, reload the page
                    if (data.success === "true") {
                        // swal({
                        //     title: "Данные сохранены",
                        //     text: "Страница будет перезагружена\nTODO: перезагрузка будет убрана в ближайшее время!",
                        //     type: "success"
                        // }, function(){ window.location.reload(); }
                        // );
                        // FIXME: Убрать перезагрузку?
                        $.jGrowl(
                            "Комментарий успешно сохранён. Страница будет перезагружена",
                            { position: 'bottom-right' }
                        );
                        setTimeout(function() {window.location.reload();}, 500);
                        // FIXME: update #comments block instead of reload!
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