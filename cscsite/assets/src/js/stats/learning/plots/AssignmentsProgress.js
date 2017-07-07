import * as d3 from "d3";
import * as c3 from "c3";
import $ from 'jquery';
import mix from '../../MixinBuilder';
import FilteredPlot from './FilteredPlot';
import AssignmentsFilterMixin from './AssignmentsFilterMixin';

class AssignmentsProgress extends mix(FilteredPlot).with(AssignmentsFilterMixin) {
    // Сейчас это попадает в AssignmentsProgress.prototype
    i18n = {
        lang: 'ru',
        ru: {
            titles: "Задания",
            participants: "Слушатели курса",
            passed: "Сдали задание",
            no_assignments: "Заданий не найдено."
        }
    };

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
        let participants = [this.i18n.ru.participants],
            passed = [this.i18n.ru.passed],
            titles = [];
        rawJSON
            .filter((a) => this.matchFilters(a, "assignment"))
            .forEach((assignment) => {
                titles.push(assignment.title);
                let _passed = 0,
                    _participants = 0;
                assignment.assigned_to
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
            $('#' + this.id).html(this.i18n.ru.no_assignments);
            return;
        }

        this.plot = c3.generate({
            bindto: '#' + this.id,
            oninit: () => { this.renderFilters() },
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
    getFilterFormData = () => {
        let self = this;
        let data = [
            // Filter by student gender
            {
                id: `#${this.id}-gender-filter`,
                html: this.templates.filters.gender({
                    filterId: `${this.id}-gender-filter`
                }),
                callback: function () {
                    $(this.id).selectpicker('render')
                        .on('changed.bs.select', function () {
                            self.filters.state["student.gender"] = this.value;
                        });
                }
            },
            // Filter by `is_online`
            {
                id: `#${this.id}-is-online-filter`,
                html: this.templates.filters.isOnline({
                    filterId: `${this.id}-is-online-filter`,
                }),
                callback: function () {
                    $(this.id).selectpicker('render')
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
                html: this.templates.filters.submitButton()
            }
        ];
        return data.filter((e) => e);
    };
}

export default AssignmentsProgress;