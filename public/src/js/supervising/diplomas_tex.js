import ZeroClipboard from 'zeroclipboard';

if (document.getElementById('diplomas-code') !== null) {
    // Highlight TeX code
    $('pre code').each(function(i, block) {
        hljs.highlightBlock(block);
    });

    if (ZeroClipboard.isFlashUnusable()) {
        $('#diplomas-code .btn-clipboard').html('Enable Flash to activate <b>copy</b> feature');
    }

    ZeroClipboard.config({
      swfPath: require('zeroclipboard/dist/ZeroClipboard.swf')
    });

    // Copy to clipboard
    var client = new ZeroClipboard( $(".btn-clipboard") );
    client.on({
        copy: function(e) {
            var text = $(e.target).next('code').text();
            client.setText(text);
            $(e.target).text('Copied!');
        },
        aftercopy: function(e) {
            setTimeout(function() { $(e.target).text("Copy")}, 700);
        },
        complete: function(client, args) {
        },
        error: function(e) {
            ZeroClipboard.destroy();
        }
    });

}
