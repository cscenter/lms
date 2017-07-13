import * as d3 from "d3";
import * as c3 from "c3";
import $ from 'jquery';
import {URLS} from 'stats/utils';
import i18n from 'stats/i18n';
import PlotOptions from "stats/PlotOptions";


export default class CampaignsStages extends PlotOptions {
    static PLOT_TYPES = {
        "universities": {
            type: "universities",
            entry_point: "api:stats_admission_campaign_stages_by_university",
            x_axis: "university__name"
        },
        "courses": {
            type: "courses",
            entry_point: "api:stats_admission_campaign_stages_by_course",
            x_axis: "course"
        }
    };
    static ENTRY_POINTS = {
        universities: "api:stats_admission_campaign_stages_by_university",
        courses: "api:stats_admission_campaign_stages_by_course",
    };

    constructor(id, options) {
        super();
        this.id = id;
        this.templates = options.templates || {};

        let values = ['application_form', 'testing', 'examination', 'interviewing'];
        this.state = {
            type: this.constructor.PLOT_TYPES.universities.type,
            campaignId: options.campaignId,
            data: {
                type: 'bar',
                groups: [values],
                keys: {
                    x: this.constructor.PLOT_TYPES.universities.x_axis,
                    value: values,
                },
                names: {
                    application_form: i18n.stages.application_form,
                    testing: i18n.stages.testing,
                    examination: i18n.stages.examination,
                    interviewing: i18n.stages.interviewing,
                },
                json: [],
                order: null, // https://github.com/c3js/c3/issues/1945
                unload: true
            }
        };

        this.plot = c3.generate({
            axis: {
                x: {
                    type: 'category',
                    height: 50,
                    tick: {
                        format: function (x) {
                            let s = this.categoryName(x);
                            if (s.length > 16) {
                                return `${s.substring(0, 16)}...`;
                            }
                            return s;
                        }
                    }
                }
            },
            tooltip: {
                format: {
                    title: (x) => {
                        return this.plot.category(x);
                    },
                }
            },
            color: {
                pattern: ['#5cb85c', '#f96868', '#F6BE80', '#515492']
            },
            bindto: '#' + this.id,
            oninit: () => {
                this.appendOptionsForm()
            },
            data: this.state.data
        });
        // FIXME: Добавить эту логику в отдельный метод? Она же используется в submitHandler
        this.getStats(this.state.campaignId)
            .then(this.convertData)
            .done(this.render);
    }

    getStats(campaignId) {
        let entryPointURL = this.constructor.ENTRY_POINTS[this.state.type];
        let dataURL = URLS[entryPointURL](campaignId);
        return $.getJSON(dataURL);
    }

    convertData = (json) => {
        this.state.data.json = json;
        return json;
    };

    render = (json) => {
        this.plot.load(this.state.data);
        return json;
    };

    getOptions = () => {
        let data = [
            {
                options: {
                    filterName: "Вид",
                    id: this.id + "-select",
                    selected: this.state.type,
                    items: [
                        {name: 'Университеты', value: 'universities'},
                        {name: 'Курсы', value: 'courses'},
                    ]
                },
                template: this.templates.select,
            },
            // Submit button
            {
                isSubmitButton: true,
                template: this.templates.submitButton,
                options: {value: "Выбрать"}
            }
        ];
        return data;
    };

    submitButtonHandler = () => {
        let newState = $(`#${this.id}-select`).val();
        // TODO: cache query
        if (newState !== this.state.type &&
            newState in this.constructor.PLOT_TYPES) {
            this.state.type = this.constructor.PLOT_TYPES[newState].type;
            this.state.data.keys.x = this.constructor.PLOT_TYPES[newState].x_axis;
            this.getStats(this.state.campaignId)
                .then(this.convertData)
                .done(this.render);
        }
        return false;
    };
}
