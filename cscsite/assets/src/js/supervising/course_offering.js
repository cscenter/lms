// TODO: dynamically load templates

const modalWrapper = $("#modal-container");

export default function unreadNotifications() {
    $('.show_unread_notifications').click(function (e) {
        e.preventDefault();
        $.get(this.href, function (data) {
            let items = '';
            data.forEach((item) => {
               items += `<li>${item.user.last_name} ${item.user.first_name}</li>`;
            });
            let ul = `<ul class="list-unstyled">${items}</ul>`;
            $('.modal-header', modalWrapper).html("Кто не прочитал новость на сайте <button type=\"button\" class=\"close\" data-dismiss=\"modal\" aria-hidden=\"true\">×</button>");
            $('.modal-body', modalWrapper).html(ul);
            modalWrapper.modal('show');
        }).fail((data) => {
            if (data.status === 403) {
                $.jGrowl(
                    'Доступ запрещён.',
                    { position: 'bottom-right', theme: 'error' }
                );
                $(this).remove();
            }
        });
    });
};