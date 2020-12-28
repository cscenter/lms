import $ from 'jquery';
import "jasny-bootstrap/js/fileinput";

import UberEditor from "components/editor";
import {createNotification} from "../utils";

const comment = $('.assignment-comment');
const modalFormWrapper = $("#update-comment-model-form");

const commentButton = $("#add-comment");
const commentForm = $('#comment-form-wrapper');
const solutionButton = $("#add-solution");
const solutionForm = $('#solution-form-wrapper');

const fn = {
    Launch: function () {
        fn.initCommentForm();
        fn.initSolutionForm();
        fn.initCommentModal();
        fn.initFileInput();
    },

    initCommentForm: function() {
        commentButton.on('click', function() {
            commentForm.removeClass('hidden');
            UberEditor.reflowEditor(commentForm);
            $(this).addClass('active');
            if (solutionForm.length > 0) {
                solutionForm.addClass('hidden');
                solutionButton.removeClass('active');
            }
        });
    },

    initSolutionForm: function() {
        if (solutionForm.length > 0) {
            solutionButton.on('click', function() {
                solutionForm.removeClass('hidden');
                UberEditor.reflowEditor(solutionForm);
                $(this).addClass('active');
                commentForm.addClass('hidden');
                commentButton.removeClass('active');
            });
        }

    },

    initCommentModal: function () {
        modalFormWrapper.modal({
            show: false
        });
        // Show EpicEditor when modal shown
        modalFormWrapper.on('shown.bs.modal', function (event) {
            const textarea = $(event.target).find('textarea').get(0);
            UberEditor.init(textarea);
            modalFormWrapper.css('opacity', '1');

        });
        // Show modal
        $('.__edit', comment).click(function (e) {
            e.preventDefault();
            const $this = $(this);
            $.get(this.href, function (data) {
                modalFormWrapper.css('opacity', '1');
                $('.inner', modalFormWrapper).html(data);
                modalFormWrapper.modal('toggle');
            }).fail(function (data) {
                if (data.status === 403) {
                    const msg = 'Доступ запрещён. Вероятно, время редактирования комментария истекло.';
                    createNotification(msg, 'error');
                    $this.remove();
                }
            });
        });

        modalFormWrapper.on('submit', 'form', fn.onSubmitCommentModalForm);
    },

    onSubmitCommentModalForm: function(event) {
        event.preventDefault();
        let form = event.target;
        // TODO: validate empty comment here
        $.ajax({
            url : form.action,
            type : "POST",
            data : $(form).serialize(),
        })
        .done(function (json) {
            if (json.success === 1) {
                modalFormWrapper.modal('hide');
                let target = comment.filter(function() {
                  return $(this).data("id") == json.id
                });
                const textElement = $('.ubertext', target);
                textElement.html(json.html);
                UberEditor.render(textElement.get(0));
                createNotification('Комментарий успешно отредактирован.');
            } else {
                createNotification('Комментарий не был сохранён.', 'error');
            }
        })
        .fail(function () {
            createNotification('Комментарий не был сохранён.', 'error');
        });
        return false;
    },

    initFileInput: function() {
        $('.jasny.fileinput')
            .on('clear.bs.fileinput', function(event) {
                $(event.target).find('.fileinput-clear-checkbox').val('on');
                $(event.target).find('.fileinput-filename').text('Файл не выбран');
            })
            .on('change.bs.fileinput', function(event) {
                $(event.target).find('.fileinput-clear-checkbox').val('');
            })
            .on('reseted.bs.fileinput', function(event) {
                $(event.target).find('.fileinput-filename').text('Файл не выбран');
                $(event.target).find('.fileinput-clear-checkbox').val('');
            });
    },
};

$(document).ready(function () {
    fn.Launch();
});
