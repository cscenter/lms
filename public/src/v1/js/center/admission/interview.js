import UberEditor from "editor";
import 'jquery-bar-rating';
import {createNotification} from "utils";
import {restoreTabFromHash} from './utils';

const ratingSelect = $("select#id_score");
const commentForm = $("#comment form");
const assignmentsWrapper = $(".assignments-multicheckbox");
const assignmentPreviewWrapper = $("#interview-assignment-model-form");

function initInterviewCommentForm() {
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
                createNotification("Комментарий успешно сохранён. Страница будет перезагружена");
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

function initRatingBar() {
    ratingSelect.barrating({
        theme: 'bars-movie',
    });
}

function initAssignmentsCheckboxes() {
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
}

export default function initInterviewSection() {
    restoreTabFromHash();
    initInterviewCommentForm();
    initRatingBar();
    initAssignmentsCheckboxes();
}