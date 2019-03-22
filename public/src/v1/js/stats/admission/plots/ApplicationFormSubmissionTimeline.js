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
                    value: [
                        "2017",
                        "2018",
                        "2019",
                    ],
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
        let json = [];
        rawJSON.forEach((item) => {
            const paddedDay = item.day.toString().padStart("2", "0");
            const paddedMonth = item.month.toString().padStart("2", "0");
            json.push({
                [item.year]: item.total,
                'date': `${paddedDay}.${paddedMonth}`,
            });
        });
        this.state.data.json = json;
        console.log(json);
        return json;
    };

    reflow = (json) => {
        this.plot.load(this.state.data);
        return json;
    };
}
