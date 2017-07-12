import * as d3 from "d3";
import * as c3 from "c3";
import $ from 'jquery';
import {GROUPS, URLS} from 'stats/utils';
import i18n from 'stats/i18n';

class CampaignResultsStudents {
    static ENTRY_POINT_URL = "api:stats_admission_campaign_students_results";

    constructor(id, options) {
        this.id = id;
        this.groups = GROUPS;

        this.state = {
            data: {
                type: 'pie',
                columns: [],
                order: null, // https://github.com/c3js/c3/issues/1945
            }
        };

        this.plot = c3.generate({
            bindto: this.id,
            tooltip: {
                format: {
                    value: (value, ratio, id) => {
                        return value + i18n.people_suffix;
                    }
                }
            },
            data: this.state.data
        });
        let promise = options.apiRequest || this.getStats(options.campaign_id);
        promise
            .then(this.convertData)
            .then(this.render)
            .done(this.appendParticipantsInfo);
    }

    getStats(campaign_id) {
        let dataURL = URLS[this.constructor.ENTRY_POINT_URL](campaign_id);
        return $.getJSON(dataURL);
    }

    convertData = (rawJSON) => {
        let columns = [];
        rawJSON.forEach((e) => {
            columns.push([this.groups[e.group], e.students]);
        });
        this.state.data.columns = columns;
        return rawJSON;
    };

    render = (columns) => {
        this.plot.load(this.state.data);
        return columns;
    };

    appendParticipantsInfo = (rawJSON) => {
        let total = 0;
        rawJSON.forEach((e) => {
            total += e.students;
        });
        d3.select(this.id).insert('div', ":first-child")
            .attr('class', 'info')
            .selectAll('div')
            .data([total])
            .enter()
            .append('div')
            .text(d => this.i18n.total_participants + ': ' + d);
    };
}

export default CampaignResultsStudents;