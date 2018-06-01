export function restoreTabFromHash() {
    let hash = window.location.hash;
    hash && $('ul.nav a[href="' + hash + '"]').tab('show');

    $('.nav-tabs a').click(function (e) {
        $(this).tab('show');
        const scrollmem = $('body').scrollTop() || $('html').scrollTop();
        $('html,body').scrollTop(scrollmem);
    });
}