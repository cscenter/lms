import * as d3 from "d3";
import * as c3 from "c3";
import $ from 'jquery';
import mix from '../../MixinBuilder';
import PlotOptions from 'stats/PlotOptions';
import AssignmentsFilterMixin from './AssignmentsFilterMixin';
import i18n from 'stats/i18n';

class AssignmentsProgress extends mix(PlotOptions).with(AssignmentsFilterMixin) {

    constructor(id, options) {
        super(id, options);
        this.id = id;
        this.type = 'line';
        this.rawJSON = {};
        this.templates = options.templates || {};

        this.state = {
            data: [],  // filtered data
            titles: undefined,  // assignment titles
        };
        this.plot = undefined;
        const promise = options.apiRequest ||
                      this.constructor.getStats(options.course_session_id);
        promise
            // Memorize raw JSON data for future conversions
            .then((rawJSON) => { this.rawJSON = rawJSON; return rawJSON })
            .then(this.calculateFilterProps)
            .then(this.convertData)
            .done(this.render);
    }

    static getStats(course_session_id) {
        const dataURL = window.URLS["api:stats_assignments"](course_session_id);
        return $.getJSON(dataURL);
    }

    // Recalculate data based on current filters state
    convertData = (rawJSON) => {
        let participants = [i18n.assignments.participants],
            passed = [i18n.assignments.passed],
            titles = [];
        rawJSON
            .filter((a) => this.matchFilters(a, "assignment"))
            .forEach((assignment) => {
                titles.push(assignment.title);
                let _passed = 0,
                    _participants = 0;
                assignment.students
                    .filter((sa) => this.matchFilters(sa, "student_assignment"))
                    .forEach((sa) => {
                       _participants += 1;
                       _passed += sa.sent;
                });
                participants.push(_participants);
                passed.push(_passed);
        });
        this.state.titles = titles;
        this.state.data = [participants, passed];
        return this.state.data;
    };

    render = (data) => {
        if (!this.state.titles.length) {
            $('#' + this.id).html(i18n.assignments.no_assignments);
            return;
        }

        this.plot = c3.generate({
            bindto: '#' + this.id,
            oninit: () => { this.appendOptionsForm() },
            data: {
                type: this.type,
                columns: data
            },
            tooltip: {
                format: {
                    title: (d) => {
                        if (this.state.titles[d] !== void 0) {
                            return this.state.titles[d].slice(0, 80);
                        } else {
                            return "";
                        }
                    },
                }
            },
            axis: {
              x: {
                tick: {
                  format: function (x) { return x + 1; }
                }
              }
            },
            grid: {
                y: {
                    show: true
                }
            }
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
            this.filterDataCurriculumYear(),  // could return null
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
        let data = this.convertData(this.rawJSON);
        this.plot.load({
            type: this.type,
            columns: data,
            // Clean plot if no data, otherwise save animation transition
            unload: this.state.titles.length > 0 ? {} : true,
        });
        return false;
    };
}

export default AssignmentsProgress;