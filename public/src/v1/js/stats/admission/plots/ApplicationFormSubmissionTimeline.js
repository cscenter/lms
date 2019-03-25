import * as d3 from "d3";
import * as c3 from "c3";
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
                keys: {
                    x: 'date',
                    value: [],
                },
                json: [],
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
                    type: 'categories',
                    tick: {
                        multiline: false,
                        rotate: 90
                    }
                }
            },
            subchart: {
                show: true
            },
            data: this.state.data
        });
        let promise = options.apiRequest || this.getStats(options.cityCode);
        promise
            .then(this.convertData)
            .done(this.reflow);
    }

    getStats(cityCode) {
        let dataURL = `/api/v1/stats/admission/cities/${cityCode}/applicants/form-submissions/`;
        return $.getJSON(dataURL);
    }

    convertData = (rawJSON) => {
        const {date, ...years} = rawJSON[0];
        this.state.data.json = rawJSON;
        this.state.data.keys.value = Object.keys(years);
        return rawJSON;
    };

    reflow = (json) => {
        this.plot.load(this.state.data);
        return json;
    };
}
