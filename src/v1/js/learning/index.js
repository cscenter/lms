import $ from 'jquery';
import "jasny-bootstrap/js/fileinput";

import UberEditor from "../editor";
import {createNotification, showComponentError} from "../utils";
import {TIMEPICKER_ICONS, TIMEPICKER_TOOLTIPS} from "../conf";

const sidebar = $("#o-sidebar");
const footer = $(".footer");
const comment = $('.assignment-comment');
const modalFormWrapper = $("#update-comment-model-form");

let editor;

const fn = {
    Launch: function () {
        fn.initCommentModal();
        fn.initStickySidebar();
        fn.initFileInput();

        const timePickers = $('.timepicker');
        if (timePickers.length > 0) {
            import(/* webpackChunkName: "bootstrap-datetimepicker" */ 'eonasdan-bootstrap-datetimepicker/build/css/bootstrap-datetimepicker.min.css');
            import('forms')
                .then(_ => {
                    timePickers.datetimepicker({
                        locale: 'ru',
                        format: 'HH:mm',
                        stepping: 1,
                        useCurrent: false,
                        allowInputToggle: false,
                        icons: TIMEPICKER_ICONS,
                        tooltips: TIMEPICKER_TOOLTIPS,
                        keyBinds: {
                            left: false,
                            right: false,
                        }
                    });
                })
                .catch(error => showComponentError(error));
        }

    },

    initCommentModal: function () {
        modalFormWrapper.modal({
            show: false
        });
        // Show EpicEditor when modal shown
        modalFormWrapper.on('shown.bs.modal', function (event) {
            var textarea = $(event.target).find('textarea').get(0);
            editor = UberEditor.init(textarea);
            modalFormWrapper.css('opacity', '1');

        });
        // Show modal
        $('.__edit', comment).click(function (e) {
            e.preventDefault();
            var $this = $(this);
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

        modalFormWrapper.on('submit', 'form', fn.submitEventHandler);
    },

    submitEventHandler: function(event) {
        event.preventDefault();
        var form = event.target;
        // TODO: validate empty comment here
        $.ajax({
            url : form.action,
            type : "POST",
            data : $(form).serialize(),
        })
        .done(function (json) {
            if (json.success === 1) {
                modalFormWrapper.modal('hide');
                var target = comment.filter(function() {
                  return $(this).data("id") == json.id
                });
                var textElement = $('.ubertext', target);
                console.log(target, textElement);
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

    initStickySidebar: function () {
        if (sidebar.length > 0) {
            const sidebar_top = sidebar.offset().top - 20; // top position: 20px
            const bottom = (footer.offset().top - 75 ); // 75 - footer margin
            // 500 - random number which needs to solve fast scroll problem in chrome
            if (bottom - sidebar_top > 500 ) {
                sidebar.affix({
                    offset: {
                        top: sidebar_top,
                        bottom: (footer.outerHeight(true))
                    }
                });
                sidebar.affix('checkPosition');
            }
        }
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
                console.log(event.target);
                $(event.target).find('.fileinput-filename').text('Файл не выбран');
                $(event.target).find('.fileinput-clear-checkbox').val('');
            });
    },
};

$(document).ready(function () {
    fn.Launch();
});
