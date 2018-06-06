import ClipboardJS from 'clipboard';

if (document.getElementById('diplomas-code') !== null) {
    // Highlight TeX code
    $('pre code').each(function (i, block) {
        hljs.highlightBlock(block);
    });

    let clipboard = new ClipboardJS('.btn-clipboard', {
        target: function (trigger) {
            return trigger.nextElementSibling;
        }
    });

    clipboard.on('success', function(e) {
        $(e.trigger).text('Copied!');
        setTimeout(function () {
            $(e.trigger).text("Copy");
        }, 700);

        e.clearSelection();
    });
}
