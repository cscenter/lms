(function ($, _) {
    "use strict";

    var sidebar = $("#o-sidebar");

    var footer = $(".footer");

    var comment = $('.assignment-comment');

    var modalFormWrapper = $("#submission-comment-model-form");

    var editor;

    var fn = {
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
                editor = initUberEditor(textarea);
            });
            // Show modal
            $('.__edit', comment).click(function (e) {
                e.preventDefault();
                $.get(this.href, function (data) {
                    $('.inner', modalFormWrapper).html(data);
                    modalFormWrapper.modal('toggle');
                });
            });
            // Handle form submission
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
                if (json.success == 1) {
                    modalFormWrapper.modal('hide');
                    var target = comment.filter(function() {
                      return $(this).data("id") == json.id
                    });
                    var textElement = $('.ubertext', target);
                    textElement.html(json.html);
                    processUberText(textElement.get(0));
                    $.jGrowl('Комментарий успешно сохранён.',
                        { position: 'bottom-right'});
                } else {
                    $.jGrowl('Комментарий не был сохранён.',
                        { position: 'bottom-right', theme: 'error' });
                }
            })
            .error(function () {
                    $.jGrowl('Комментарий не был сохранён.',
                        { position: 'bottom-right', theme: 'error' });
            });
            event.stopPropagation();
            return false;
        },

        initStickySidebar: function () {
            var sidebar_top = sidebar.offset().top - 20; // top position: 20px
            var bottom = (footer.offset().top - 75 ); // 75 - footer margin
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

})(jQuery, _);