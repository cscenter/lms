import * as d3 from "d3";
import * as c3 from "c3";
import $ from 'jquery';
import {URLS} from 'stats/utils';
import i18n from 'stats/i18n';

class ParticipantsYear {
    static ENTRY_POINT_URL = "api:stats_learning_participants_year";

    constructor(id, options) {
        this.id = `#${id}`;
        this.state = {
            data: {
                type: void 0,
                x : 'x',
                unload: true,
                order: null, // https://github.com/c3js/c3/issues/1945
                columns: []
            },
            groups: []
        };
        this.plot = c3.generate({
            bindto: this.id,
            grid: {
                y: {
                    show: true
                }
            },
            tooltip: {
                grouped: false,
                format: {
                    title: () => "",
                    value: (value, ratio, id)  => {
                        return value + '&nbsp;чел.';
                    }
                }
            },
            data: this.state.data,
            oninit: this.renderSwitchButtons
        });

        let promise = options.apiRequest ||
            this.getStats(options.course_session_id);
        promise
            .then(this.convertData)
            .done(this.renderPieChart);
    }

    getStats(course_session_id) {
        let dataURL = URLS[this.constructor.ENTRY_POINT_URL](course_session_id);
        return $.getJSON(dataURL);
    }

    /**
     *  To use data both in `bar` and `pie` chart we
     *  need something like this:
     *  columns: [
     *       ['2013', 30, 0],
     *       ['2014', 0, 90],
     *       ['x', '2013', '2014'],
     *   ],
     * @returns {Array}
     */
    convertData = (rawJSON) => {
        let columns = [];
        let years = [];
        rawJSON.forEach(function (e, i) {
            const year = e.curriculum_year.toString();
            years.push(year);
            let row = new Array(rawJSON.length + 1).fill(0);
            row[0] = year;
            row[i + 1] = e.students;
            columns.push(row);
        });
        columns.push(["x"].concat(years));
        this.state.groups = [years];
        this.plot.groups(this.state.groups);
        this.state.data.columns = columns;
    };

    renderPieChart = () => {
        if (this.state.data.type === 'pie') { return; }
        this.state.data.type = 'pie';
        this.plot.load(this.state.data);
    };

    renderBarChart = () => {
        if (this.state.data.type === 'bar') { return; }
        this.state.data.type = 'bar';
        this.plot.load(this.state.data);
    };

    renderSwitchButtons = () => {
        let buttons = [
            {
                name: i18n.pieChart,
                active: this.state.data.type === void 0,
                render: this.renderPieChart
            },
            {
                name: i18n.barChart,
                active: this.state.data.type === 'bar',
                render: this.renderBarChart
            },
        ];

        d3.select(this.id)
            .insert('div', ":first-child")
            .attr('class', 'btn-group pull-right')
            .attr('role', 'group')
            .attr('aria-label', 'Toggle')
            .selectAll('button')
            .data(buttons)
            .enter().append('button').attr('class', function (d) {
                if (d.active) {
                    return 'btn btn-default active';
                } else {
                    return 'btn btn-default';
                }
            })
            .text(d => d.name)
            .on('click',  (d, i) => {
                const buttons = d3.select(this.id)
                    .select('div')
                    .selectAll('button')
                    .classed('active', false);
                d3.select(buttons[0][i]).classed('active', true);
                d.render();
            });
    };
}

export default ParticipantsYear;