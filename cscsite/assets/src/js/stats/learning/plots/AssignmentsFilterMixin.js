import {GROUPS} from "stats/utils";

let AssignmentsFilterMixin = (superclass) => class extends superclass {

    constructor(id, options) {
        super(id, options);
        this.filters = {
            // Attributes in dot-notation which should be compared
            // with filters state. See `matchFilters` for details.
            props: {
                // Attribute name must repeat object structure from rawJSON.
                assignment: ["is_online"],
                student_assignment: [
                    "student.gender",
                    "student.curriculum_year",
                    "student.groups",

                ]
            },
            choices: {
                curriculumYear: undefined,
                studentGroups: GROUPS,
            },
            // path in dot-notation from the top-level of JSON object.
            state: {
                // TODO: replace dot-notation with nested structure?
                'student.gender': undefined,
                is_online: undefined,
                'student.curriculum_year': undefined
            }
        };
    }

    /**
     * For each filter `f` from `this.filters.props[name]` get filter
     * state from `this.state.filters` and make sure `obj.f` match state value.
     * @param obj Object to compare values with filters state
     * @param name Filters collection name in dot-notation
     * @returns {bool}
     */
    matchFilters(obj, name) {
        return this.filters.props[name].reduce((a, b) => {
            let obj_value = b.split('.').reduce((a, b) => a[b], obj);
            return a && this.matchFilter(obj_value, b);
        }, true);
    }

    matchFilter = (value, stateAttrName) => {
        let stateValue = this.filters.state[stateAttrName];
        return stateValue === void 0 ||
               stateValue === "" ||
               stateValue === value ||
              (Array.isArray(value) && value.includes(stateValue));
    };

    /**
     * Collect filter choices. Don't want to calculate this data every
     * time on filter event
     * @param rawJSON JSON from REST API call
     * @returns {*}
     */
    calculateFilterProps = (rawJSON) => {
        const curriculumYearChoices = new Set();
        rawJSON.forEach(function (assignment) {
            assignment.assigned_to.forEach(function(sa) {
                curriculumYearChoices.add(sa.student.curriculum_year);
            });
        });
        this.filters.choices.curriculumYear = curriculumYearChoices;
        return rawJSON;
    };

    filterDataCurriculumYear = () => {
        if (this.filters.choices.curriculumYear.size === 0) {
            return;
        }
        let choices = [...this.filters.choices.curriculumYear].sort();
        let self = this;
        return {
            options: {
                id: this.id + "-curriculum-year-filter",
                items: choices
            },
            template: this.templates.filters.curriculumYear,
            onRendered: function () {
                $(`#${this.options.id}`).selectpicker('render')
                    .on('changed.bs.select', function () {
                        self.filters.state["student.curriculum_year"] =
                            (this.value !== "") ? parseInt(this.value) : this.value;
                    });
            }
        };
    };

    filterByStudentGroup = () => {
        if (this.filters.choices.studentGroups.size === 0) {
            return;
        }
        const choices = [];
        Object.keys(this.filters.choices.studentGroups).forEach((k) => {
           choices.push({
               value: k,
               name: this.filters.choices.studentGroups[k]
           });
        });
        let self = this;
        return {
            options: {
                filterName: "Группа",
                selected: undefined,
                id: this.id +  "-select-filter",
                items: choices
            },
            template: this.templates.filters.select,
            onRendered: function () {
                $(`#${this.options.id}`).selectpicker('render')
                    .on('changed.bs.select', function () {
                        self.filters.state["student.groups"] =
                            (this.value !== "") ? parseInt(this.value) : this.value;
                    });
            }
        };
    };
};

export default AssignmentsFilterMixin;
