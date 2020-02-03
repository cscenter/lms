import * as d3 from "d3";
import c3 from "c3";
import $ from 'jquery';
import mix from 'stats/MixinBuilder';
import PlotOptions from 'stats/PlotOptions';
import AssignmentsFilterMixin from './AssignmentsFilterMixin';
import i18n from 'stats/i18n';


class AssignmentsMeanScore extends mix(PlotOptions).with(AssignmentsFilterMixin) {

    constructor(id, options) {
        super(id, options);
        this.id = id;
        this.type = 'bar';
        this.rawJSON = {};
        this.plot = undefined;
        this.templates = options.templates || {};

        this.state = {
            data: [],  // filtered data
            titles: undefined,  // assignment titles
        };

        let promise = options.apiRequest ||
                      this.constructor.getStats(options.course_session_id);
        promise
            // Memorize raw JSON data for future conversions
            .then((rawJSON) => { this.rawJSON = rawJSON; return rawJSON })
            .then(this.calculateFilterProps)
            .then(this.convertData)
            .done(this.render);
    }

    static getStats(course_session_id) {
        let dataURL = window.URLS["stats-api:stats_assignments"](course_session_id);
        return $.getJSON(dataURL);
    }

    convertData = (rawJSON) => {
        let titles = [];
        let rows = [
            [i18n.assignments.lines.pass, i18n.assignments.lines.mean,
                i18n.assignments.lines.max]
        ];

        rawJSON
            .filter((a) => this.matchFilters(a, "assignment"))
            .forEach((assignment) => {
                titles.push(assignment.title);
                let sum = 0,
                    cnt = 0;
                assignment.students
                    .filter((sa) => this.matchFilters(sa, "student_assignment"))
                    .forEach((student) => {
                        if (student.score !== null) {
                            sum += student.score;
                            cnt += 1;
                        }
                });
                let mean = (cnt === 0) ? 0 : (sum / cnt).toFixed(1);
                rows.push([assignment.passing_score, mean, assignment.maximum_score]);
        });

        this.state.titles = titles;
        this.state.data = rows;
        return this.state.data;
    };

    render = (data) => {
        if (!this.state.titles.length) {
            $('#' + this.id).html(i18n.assignments.no_assignments);
            return;
        }

        // Let's generate here, a lot of troubles with c3.load method right now
        this.plot = c3.generate({
            bindto: '#' + this.id,
            oninit: () => { this.appendOptionsForm() },
            data: {
                type: this.type,
                order: null, // https://github.com/c3js/c3/issues/1945
                rows: data
            },
            tooltip: {
                format: {
                    title: (d) => this.state.titles[d],
                }
            },
            axis: {
              x: {
                tick: {
                  format: function (x) { return x + 1; }
                }
              }
            },
            legend: {
                position: 'bottom'
            },
            grid: {
                y: {
                    show: true
                }
            },
        });
    };

    /**
     * Collect filter elements data which will be appended right after plot
     * with d3js. Each element must have `html` attribute. Callback is optional.
     * @returns {[*,*]}
     */
    getOptions = () => {
        let self = this;
        let data = [
            // Filter by student gender
            {
                options: {
                    id: `${this.id}-gender-filter`
                },
                template: this.templates.filters.gender,
                onRendered: function () {
                    $(`#${this.options.id}`).selectpicker('render')
                        .on('changed.bs.select', function () {
                            self.filters.state["student.gender"] = this.value;
                        });
                }
            },
            // Filter by `is_online`
            {
                options: {
                    id: `${this.id}-is-online-filter`,
                },
                template: this.templates.filters.isOnline,
                onRendered: function () {
                    $(`#${this.options.id}`).selectpicker('render')
                        .on('changed.bs.select', function () {
                            self.filters.state.is_online = (this.value === "") ?
                                undefined : (this.value === "true");
                        });
                }
            },
            // Filter by curriculum year
            this.filterDataCurriculumYear(),  // can return null
            this.filterByStudentGroup(),
            // Submit button
            {
                isSubmitButton: true,
                template: this.templates.filters.submitButton,
                options: {}
            }
        ];
        return data.filter((e) => e);
    };

    submitButtonHandler = () => {
        let filteredData = this.convertData(this.rawJSON);
        this.plot.load({
            type: this.type,
            rows: filteredData,
            // Clean plot if no data, otherwise save animation transition
            unload: this.state.titles.length > 0 ? {} : true
        });
        return false;
    };
}

export default AssignmentsMeanScore;