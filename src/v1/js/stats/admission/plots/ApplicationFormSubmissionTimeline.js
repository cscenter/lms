import c3 from "c3";
import $ from 'jquery';
import {URLS} from 'stats/utils';
import i18n from 'stats/i18n';
import {COLOR_PALETTE} from "../../utils";


export default class ApplicationFormSubmissionTimeline {

    constructor(id, options) {
        this.id = id;

        this.state = {
            data: {
                type: 'bar',
                columns: [],
                order: null, // https://github.com/c3js/c3/issues/1945
            }
        };


        this.plot = c3.generate({
            bindto: this.id,
            color: {
                pattern: COLOR_PALETTE
            },
            axis: {
                x: {
                    type: 'category',
                    tick: {
                        format: function (x) { return x + 1 },
                        multiline: false,
                        rotate: 90
                    }
                }
            },
            tooltip: {
                format: {
                    title: (x) => {
                        return `день ${x + 1}`;
                    },
                }
            },
            data: this.state.data
        });
        let promise = options.apiRequest || this.getStats(options.branchId);
        promise
            .then(this.convertData)
            .done(this.reflow);
    }

    getStats(branchId) {
        let dataURL = `/api/v1/stats/admission/branches/${branchId}/applicants/form-submissions/`;
        return $.getJSON(dataURL);
    }

    convertData = (rawJSON) => {
        let columns = [];
        Object.keys(rawJSON).forEach(year => {
          let values = rawJSON[year];
          columns.push([year, ...values]);
        });
        this.state.data.columns = columns;
        return rawJSON;
    };

    reflow = (json) => {
        this.plot.load(this.state.data);
        return json;
    };
}
