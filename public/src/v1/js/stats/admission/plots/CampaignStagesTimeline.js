import c3 from "c3";
import $ from 'jquery';
import {URLS} from 'stats/utils';
import i18n from 'stats/i18n';


/**
 * Renders plot with stages statistics by years for target branch
 */
export default class CampaignStagesTimeline {
    static ENDPOINT_URI = "stats-api:stats_admission_campaigns_stages_by_year";

    constructor(id, options) {
        this.id = id;

        this.state = {
            data: {
                type: 'spline',
                keys: {
                    x: 'campaign__year',
                    value: ['application_form', 'testing', 'examination', 'interviewing'],
                },
                names: {
                    application_form: i18n.stages.application_form,
                    testing: i18n.stages.testing,
                    examination: i18n.stages.examination,
                    interviewing: i18n.stages.interviewing,
                },
                json: [],
                order: null, // https://github.com/c3js/c3/issues/1945
            }
        };

        this.plot = c3.generate({
            bindto: this.id,
            data: this.state.data
        });
        let promise = options.apiRequest || this.getStats(options.branchId);
        promise
            .then(this.convertData)
            .done(this.reflow);
    }

    getStats(branchId) {
        let dataURL = URLS[this.constructor.ENDPOINT_URI](branchId);
        return $.getJSON(dataURL);
    }

    convertData = (rawJSON) => {
        this.state.data.json = rawJSON;
        return rawJSON;
    };

    reflow = (columns) => {
        this.plot.load(this.state.data);
        return columns;
    };
}
