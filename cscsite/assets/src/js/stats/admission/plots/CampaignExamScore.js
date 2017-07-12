import * as d3 from "d3";
import * as c3 from "c3";
import $ from 'jquery';
import {URLS} from 'stats/utils';
import i18n from 'stats/i18n';


export default class CampaignExamScore {
    static ENTRY_POINT_URL = "api:stats_admission_campaign_exam_score";

    constructor(id, options) {
        this.id = id;

        this.state = {
            data: {
                type: 'bar',
                keys: {
                    x: 'score',
                    value: ['total'],
                },
                names: {
                    total: i18n.total
                },
                json: [],
                // order: null, // https://github.com/c3js/c3/issues/1945
            }
        };

        this.plot = c3.generate({
            bindto: this.id,
            legend: {
                show: false
            },
            tooltip: {
                format: {
                    title: (value) => {
                        return value + i18n.score_suffix;
                    }
                }
            },
            // axis: {
            //     x: {
            //         tick: {
            //             culling: false
            //         }
            //     }
            // },
            color: {
                pattern: ['#36abe5']
            },
            data: this.state.data
        });
        let promise = options.apiRequest || this.getStats(options.campaignId);
        promise
            .then(this.convertData)
            .done(this.render);
    }

    getStats(campaignId) {
        let dataURL = URLS[this.constructor.ENTRY_POINT_URL](campaignId);
        return $.getJSON(dataURL);
    }

    convertData = (rawJSON) => {
        this.state.data.json = rawJSON;
        return rawJSON;
    };

    render = (columns) => {
        this.plot.load(this.state.data);
        return columns;
    };
}
