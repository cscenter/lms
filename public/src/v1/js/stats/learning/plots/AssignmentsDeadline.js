import * as d3 from "d3";
import * as c3 from "c3";
import $ from 'jquery';
import {createDuration} from 'moment/src/lib/duration/duration';
import mix from '../../MixinBuilder';
import PlotOptions from 'stats/PlotOptions';
import AssignmentsFilterMixin from './AssignmentsFilterMixin';
import i18n from 'stats/i18n';


class AssignmentsDeadline extends mix(PlotOptions).with(AssignmentsFilterMixin) {

    constructor(id, options) {
        super(id, options);
        // Remove
        this.id = id;
        this.type = 'bar';
        this.rawJSON = {};
        this.plot = undefined;
        this.templates = options.templates || {};

        this.state = {
            data: [],  // filtered data
            titles: undefined,  // assignment titles
        };

        // Order is unspecified for Object, but I believe browsers sort
        // it in a proper way
        // FIXME: set explicitly?
        this.types = Object.keys(i18n.submissions.deadline_types).reduce((m, k) => {
            return m.set(k, i18n.submissions.deadline_types[k]);
        }, new Map());

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
        let dataURL = window.URLS["api:stats_assignments"](course_session_id);
        return $.getJSON(dataURL);
    }

    // Convert diff between first submission and deadline to plot column type
    toType(deadline_at, submitted_at) {
        if (submitted_at === null) {
            return this.types.get("no_submission");
        }
        let diff_ms = deadline_at - new Date(submitted_at);
        if (diff_ms <= 0) {
            return this.types.get("after");
        } else {
            let diff = new createDuration(diff_ms),
                inDays = diff.asDays();
            if (inDays >= 7) {
                return this.types.get("gte7days");
            } else if (inDays >= 1) {
                return this.types.get("lte1to6days");
            } else {
                let inHours = diff.asHours();
                if (inHours >= 3) {
                    return this.types.get("lte3to24hours");
                } else {
                    return this.types.get("lt3hours");
                }
            }
        }
    }

    convertData = (jsonData) => {
        let types = Array.from(this.types.values()),
            titles = [],
            rows = [types];
        jsonData
            .filter((a) => a.is_online !== false)
            .forEach((assignment) => {
                titles.push(assignment.title);
                let deadline = new Date(assignment.deadline_at);
                let counters = types.reduce(function (a, b) {
                        return a.set(b, 0);
                    }, new Map());
                assignment.students
                    .filter((s) => this.matchFilters(s, "student_assignment"))
                    .forEach((student) => {
                        let type = this.toType(deadline, student.first_submission_at);
                        if (type !== undefined) {
                            counters.set(type, counters.get(type) + 1);
                        } else {
                            // console.debug("Unknown deadline type for: ", student);
                        }
                    });
                rows.push(Array.from(counters, ([k, v]) => v));
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
                rows: data,
                order: null, // https://github.com/c3js/c3/issues/1945
                groups: [
                    Array.from(this.types, ([k, v]) => v)
                ]
            },
            tooltip: {
                format: {
                    title: (d) => { return this.state.titles[d] },
                }
            },
            axis: {
                x: {
                    tick: {
                      format: function (x) { return ""; }
                    }
                }
            },
            color: {
                pattern: ['#2ca02c', '#9c27b0', '#ffbb78', '#ff7f0e', '#d62728', '#9467bd', '#c5b0d5', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d', '#17becf', '#9edae5']
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

    // Ignore students curriculum year who didn't send submission at all
    calculateFilterProps = (rawJSON) => {
        const curriculumYearChoices = new Set();
        rawJSON.forEach(function (assignment) {
            assignment.students
                .filter((s) => { return s.first_submission_at !== null })
                .forEach(function(sa) {
                    curriculumYearChoices.add(sa.student.curriculum_year);
                });
        });
        this.filters.choices.curriculumYear = curriculumYearChoices;
        return rawJSON;
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
                // id: `#${this.id}-gender-filter`,
                options: {id: `${this.id}-gender-filter`},
                template: this.templates.filters.gender,
                onRendered: function () {
                    $(`#${this.options.id}`).selectpicker('render')
                        .on('changed.bs.select', function () {
                            self.filters.state["student.gender"] = this.value;
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

export default AssignmentsDeadline;