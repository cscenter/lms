import * as d3 from "d3";
import * as c3 from "c3";
import $ from 'jquery';
import {URLS} from 'stats/utils';
import i18n from 'stats/i18n';
import {COLOR_PALETTE} from "../../utils";


export default class ApplicantsResultsTimeline {
    static ENTRY_POINT_URL = "api:stats_admission_campaign_applicants_results";

    constructor(id, options) {
        this.id = id;

        this.state = {
            data: {
                type: 'bar',
                keys: {
                    x: 'campaign__year',
                    value: [
                        "accept",
                        "accept_if",
                        "volunteer",
                        "rejected_interview",
                        "they_refused",
                    ],
                },
                names: i18n.statuses,
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
                    type: 'categories'
                }
            },
            data: this.state.data
        });
        let promise = options.apiRequest || this.getStats(options.cityCode);
        promise
            .then(this.convertData)
            .done(this.reflow);
    }

    getStats(cityCode) {
        let dataURL = URLS[this.constructor.ENTRY_POINT_URL](cityCode);
        return $.getJSON(dataURL);
    }

    convertData = (json) => {
        this.state.data.json = json;
        return json;
    };

    reflow = (json) => {
        this.plot.load(this.state.data);
        return json;
    };
}
