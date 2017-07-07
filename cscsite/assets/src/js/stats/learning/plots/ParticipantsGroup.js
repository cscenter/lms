import * as d3 from "d3";
import * as c3 from "c3";
import $ from 'jquery';
import {GROUPS} from 'stats/utils';

class ParticipantsGroup {

    i18n = {
        ru: {
            groups: {
                STUDENT_CENTER: "Студент центра",
                VOLUNTEER: "Вольнослушатель",
                GRADUATE: "Выпускник",
                MASTERS_DEGREE: "Магистр АУ"
            },
            total_participants: "Всего слушателей курса"
        }
    };

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
                        return value + '&nbsp;чел.';
                    }
                }
            },
            data: this.state.data
        });
        let promise = options.apiRequest ||
                      this.constructor.getStats(options.course_session_id);
        promise
            .then(this.convertData)
            .then(this.render)
            .done(this.appendParticipantsInfo);
    }

    static getStats(course_session_id) {
        let dataURL = window.URLS["api:stats_learning_participants_group"](course_session_id);
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
            .text(d => this.i18n.ru.total_participants + ': ' + d);
    };
}

export default ParticipantsGroup;