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

            fn.newInterviewForm();

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
                }).fail(function (data) {
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
                const data = commentForm.serializeArray();
                $.ajax({
                    url: commentForm.attr("action"),
                    data: data,
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
        },

        newInterviewForm: function () {
            const wrapper = $(".admission-applicant-page #create");
            wrapper.find("select[name=interview_from_stream-stream]")
                .change({wrapper: wrapper}, fn.InterviewSlotsHandler);
        },

        InterviewSlotsHandler: function (event) {
            const wrapper = event.data.wrapper;
            const streamSelect = wrapper.find("select[name=interview_from_stream-stream]");
            const slotSelect = wrapper.find("select[name='interview_from_stream-slot']");
            const streamID = parseInt(streamSelect.val());
            if (!isNaN(streamID)) {
                slotSelect
                // FIXME: По-хорошему надо запоминать предыдущее успешное состояние. Если оно не меняется - избегать запросов. datepicker должен ещё какое-то событие посылать, если значение не валидно и он выставляет сам предыдущее...
                    .find('option')
                    .remove();
                // TODO: Replace url with data from js_reverse?
                $.ajax({
                    dataType: "json",
                    url: "/admission/interviews/slots/",
                    data: {
                        stream: streamID,
                    },
                }).done((data) => {
                    slotSelect.append($('<option>').text("---------").attr('value', ""));
                    data.forEach((slot) => {
                        let title;
                        if (slot.interview_id !== null) {
                            title = `${slot.start_at} (занято)`;
                        } else {
                            title = `${slot.start_at}`;
                        }
                        slotSelect.append($('<option>')
                            .text(title)
                            .attr('value', slot.pk)
                            .prop('disabled', slot.interview_id !== null));
                    });
                }).fail(function (xhr) {
                    console.log(xhr);
                });
            }
        },
    };

    $(document).ready(function () {
        fn.launch();
    });

})(jQuery);