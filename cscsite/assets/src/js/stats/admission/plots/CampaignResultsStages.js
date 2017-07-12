import * as d3 from "d3";
import * as c3 from "c3";
import $ from 'jquery';
import {URLS} from 'stats/utils';
import i18n from 'stats/i18n';


class CampaignResultsStages {
    static ENTRY_POINT_URL = "api:stats_admission_campaign_stages";

    constructor(id, options) {
        this.id = id;

        this.state = {
            data: {
                type: 'line',
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
                // order: null, // https://github.com/c3js/c3/issues/1945
            }
        };

        this.plot = c3.generate({
            bindto: this.id,
            data: this.state.data
        });
        let promise = options.apiRequest || this.getStats(options.cityCode);
        promise
            .then(this.convertData)
            .done(this.render);
    }

    getStats(cityCode) {
        let dataURL = URLS[this.constructor.ENTRY_POINT_URL](cityCode);
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

export default CampaignResultsStages;