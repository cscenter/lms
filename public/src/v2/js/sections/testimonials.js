import FontFaceObserver from 'fontfaceobserver';
import Masonry from 'masonry-layout';
import $ from 'jquery';

import {MOBILE_VIEWPORT_MAX} from 'utils';


export function launch() {
    if (window.screen.availWidth >= MOBILE_VIEWPORT_MAX) {
        initMasonryGrid();
    } else {
        hideBodyPreloader();
    }
}

function initMasonryGrid() {
    const font = new FontFaceObserver('Fira Sans', {
      style: 'normal',
      weight: 400,
    });
    // Make sure font has been loaded and testimonial content rendered with it
    font.load().then(function () {
        let grid = new Masonry(document.querySelector('#masonry-grid'), {
            itemSelector: '.grid-item',
            // use element for option
            columnWidth: '.grid-sizer',
            percentPosition: true,
            initLayout: false
        });
        grid.once('layoutComplete', function() {
            hideBodyPreloader();
        });
        grid.layout();
    });
}

function hideBodyPreloader() {
    $(document.body).removeClass("_fullscreen").removeClass("_loading");
}