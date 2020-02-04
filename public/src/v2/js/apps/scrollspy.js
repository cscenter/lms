import ScrollSpy from 'bootstrap5/scrollspy';

export function launch() {
    new ScrollSpy(document.body, {
        offset: 220,
        target: '#history-navigation'
    });
}
