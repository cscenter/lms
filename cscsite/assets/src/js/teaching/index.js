// Pros & Cons двух подходов: загрузить всё, выполнить одно (можно оптимизировать суммарный вес). Либо загружать динамически куски.

$(document).ready(function () {
    let section = $("body").data("init-section");
    // let's change this file a little bit to clean browser cache
    if (section === "gradebook") {
        import(/* webpackChunkName: "gradebook" */ 'teaching/gradebook').then(module => {
            const component = module.default;
            component.launch();
        });
        // TODO: show an error
    }
});
