import { select as d3Select } from 'd3-selection';

/**
 * Inherit from this class if plot has some view/filter options.
 * Add `oninit: () => { this.appendOptionsForm() },` to `c3.generate` method
 * to make it work.
 */
export default class PlotOptions {

    /**
     * Collect options which will be appended right after plot
     * with d3js. Each element must have `html` attribute. Callback is optional.
     * @returns {Array} List of {id: *, html: *, [callback: function]}
     */
    getOptions = () => {
        return [];
    };

    appendOptionsForm = () => {
        let options = this.getOptions();
        if (!options.length) {
            return;
        }
        // .col-xs-10 node
        let plotWrapperNode = d3Select('#' + this.id).node().parentNode,
            // first `nextSibling` used for skipping #text node
            // between .col-xs-10 and .col-xs-2
            filterWrapperNode = plotWrapperNode.nextSibling.nextSibling;
        d3Select(filterWrapperNode)
            .selectAll('div.form-group')
            .data(options)
            .enter()
            .append('div').attr('class', 'form-group')
            .html( (d) => { return d.template(d.options);})
            .each( (d) => {
                if (d.onRendered !== undefined) { d.onRendered(); }
            })
            // On last step, append filter button
            .filter(function(d) { return d.isSubmitButton === true })
            .on("click", this.submitButtonHandler)
    };

    submitButtonHandler = () => {
        return false;
    };
}