// import * as d3 from "d3";

class FilteredPlot {

    constructor(id, options) {
        // TODO: добавить проверку, что есть this.templates.filters.curriculumYear?
    }

    /**
     * For each filter `f` from `this.filters.props[name]` get filter
     * state from `this.state.filters` and make sure `obj.f` match state value.
     * @param obj Object to compare values with filters state
     * @param name Filters collection name in dot-notation
     * @returns {bool}
     */
    matchFilters(obj, name) {
        return this.filters.props[name].reduce((a, b) => {
            let obj_value = b.split('.').reduce((a, b) => a[b], obj);
            return a && this.matchFilter(obj_value, b);
        }, true);
    }

    matchFilter = (value, stateAttrName) => {
        let stateValue = this.filters.state[stateAttrName];
        return stateValue === void 0 ||
               stateValue === "" ||
               stateValue === value ||
               value.includes(stateValue);
    };

    renderFilters = () => {
        let data = this.getFilterFormData();
        if (!data.length) {
            return;
        }
        // .col-xs-10 node
        let plotWrapperNode = d3.select('#' + this.id).node().parentNode,
            // first `nextSibling` used for skipping #text node
            // between .col-xs-10 and .col-xs-2
            filterWrapperNode = plotWrapperNode.nextSibling.nextSibling;
        d3.select(filterWrapperNode)
            .selectAll('div.form-group')
            .data(data)
            .enter()
            .append('div').attr('class', 'form-group')
            .html( (d) => d.html)
            .each( (d) => {
                if (d.callback !== undefined) { d.callback(); }
            })
            // On last step, append filter button
            .filter(function(d) { return d.isSubmitButton === true })
            .on("click", this.submitButtonHandler)
    };

    submitButtonHandler = () => {
        let filteredData = this.convertData(this.rawJSON);
        this.plot.load({
            type: this.type,
            columns: filteredData,
            // Clean plot if no data, otherwise save animation transition
            // FIXME: убрать бы эту зависимость от state
            unload: this.state.titles.length > 0 ? {} : true
        });
        return false;
    };

    /**
     * Collect filter elements data which will be appended right after plot
     * with d3js. Each element must have `html` attribute. Callback is optional.
     * @returns {[*,*]}
     */
    getFilterFormData = () => {
        return [];
    };
}

export default FilteredPlot;