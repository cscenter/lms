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
                    "student.curriculum_year"

                ]
            },
            choices: {
                curriculumYear: undefined
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
};

export default AssignmentsFilterMixin;
