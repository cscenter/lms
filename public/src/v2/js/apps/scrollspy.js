import $ from 'jquery';
import 'bootstrap/js/src/scrollspy';

export function launch() {
    $('body').scrollspy({
        offset: 220,
        target: '#history-navigation'
    });

    // FIXME: test sentry source mapping!
    document.getElementById('year2011').addEventListener('click', function () {
        myUndefinedFunction();
    })
}
