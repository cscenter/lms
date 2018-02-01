let PlotTypeOptionMixin = (superclass) => class extends superclass {

    getPlotTypeOptionData() {
        return {
            options: {
                filterName: "Вид",
                id: this.id + "-select",
                selected: this.state.type,
                items: [
                    {name: 'Университеты', value: 'universities'},
                    {name: 'Курсы', value: 'courses'},
                ]
            },
            template: this.templates.select,
        }
    }
};

export default PlotTypeOptionMixin;