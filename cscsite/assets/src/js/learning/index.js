import $ from 'jquery';
import UberEditor from "../editor";

const sidebar = $("#o-sidebar");
const footer = $(".footer");
const comment = $('.assignment-comment');
const modalFormWrapper = $("#submission-comment-model-form");

let editor;

const fn = {
    Launch: function () {
        fn.initCommentModal();
        fn.initStickySidebar();
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
                modalFormWrapper.css('opacity', '0');
                $('.inner', modalFormWrapper).html(data);
                modalFormWrapper.modal('toggle');
            }).fail(function (data) {
                if (data.status === 403) {
                    $.jGrowl(
                        'Доступ запрещён. Вероятно, время редактирования комментария истекло.',
                        { position: 'bottom-right', theme: 'error' }
                    );
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
                textElement.html(json.html);
                UberEditor.render(textElement.get(0));
                $.jGrowl('Комментарий успешно сохранён.',
                    { position: 'bottom-right'});
            } else {
                $.jGrowl('Комментарий не был сохранён.',
                    { position: 'bottom-right', theme: 'error' });
            }
        })
        .fail(function () {
                $.jGrowl('Комментарий не был сохранён.',
                    { position: 'bottom-right', theme: 'error' });
        });
        return false;
    },

    initStickySidebar: function () {
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
    },
};

$(document).ready(function () {
    fn.Launch();
});
