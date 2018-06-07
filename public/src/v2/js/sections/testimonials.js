import FontFaceObserver from 'fontfaceobserver';
import Masonry from 'masonry-layout';


export function launch() {
    // TODO: add ajax loader first
    // TODO: disable masonry on mobile (prevent initialization on mobile and forget about resizing)
    // FIXME: What is `vendors~testimonials`?
    const font = new FontFaceObserver('Fira Sans', {
      style: 'normal',
      weight: 400,
    });
    // Make sure font has been loaded and testimonial content rendered with it
    font.load().then(function () {
        let grid = document.querySelector('#masonry-grid');
        let msnry = new Masonry(grid, {
            itemSelector: '.grid-item',
            // use element for option
            columnWidth: '.grid-sizer',
            percentPosition: true,
            // {#initLayout: false#}
        });
    });
}