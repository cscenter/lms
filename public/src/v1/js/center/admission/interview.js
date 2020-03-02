import _throttle from 'lodash-es/throttle';

import UberEditor from "editor";
import 'jquery-bar-rating';
import {createNotification} from "utils";
import {restoreTabFromHash} from './utils';

const ratingSelect = $("select#id_score");
const commentForm = $("#comment form");
const assignmentsWrapper = $(".assignments-multicheckbox");
const assignmentPreviewWrapper = $("#interview-assignment-model-form");

function handleSubmit(e) {
    $.ajax({
        type: 'POST',
        url: commentForm.attr("action"),
        data: commentForm.serialize(),
        dataType: 'json',
    }).done(function (data) {
        // FIXME: update #comments block instead of reload after migrating to react
        // Form was valid and saved, reload the page
        createNotification("Комментарий успешно сохранён. Страница будет перезагружена");
        setTimeout(function () {
            window.location.reload();
        }, 500);
    }).fail(function (jqXHR, textStatus, errorThrown) {
        if (jqXHR.status === 400) {
            swal({
                title: "",
                text: jqXHR.responseJSON.errors,
                type: "warning",
                confirmButtonText: "Хорошо"
            });
        } else {
            swal({
                title: "Всё плохо!",
                text: "Пожалуйста, скопируйте результаты своей работы и попробуйте перезагрузить страницу.",
                type: "error"
            });
        }
    });
}

const throttledSubmitHandler = _throttle(handleSubmit,  500,
    {leading: true, trailing: false});


function initInterviewCommentForm() {
    // Stupid defense from stale sessions
    commentForm.submit(function(e) {
        e.preventDefault();
        throttledSubmitHandler(e);
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

function printButtons() {
    $('._print-without-solution').click(function() {
        $('body').removeClass('_with-printable-solutions');
        window.print();
    });
    $('._print-with-solution').click(function() {
        $('body').addClass('_with-printable-solutions');
        window.print();
    });
}

export default function initInterviewSection() {
    restoreTabFromHash();
    initInterviewCommentForm();
    initRatingBar();
    initAssignmentsCheckboxes();
    printButtons();
}