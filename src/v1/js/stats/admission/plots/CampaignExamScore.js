import c3 from "c3";
import $ from 'jquery';
import {URLS} from 'stats/utils';
import i18n from 'stats/i18n';
import mix from 'stats/MixinBuilder';
import PlotOptions from "stats/PlotOptions";
import PlotTypeOptionMixin from "./PlotTypeOptionMixin";


// FIXME: Add support for ?orient=split. Course data can be sorted... :<
export default class CampaignExamScore extends mix(PlotOptions).with(PlotTypeOptionMixin) {
    static PLOT_TYPES = {
        "universities": {
            type: "universities",
            entry_point: "stats-api:stats_admission_campaign_exam_score_by_university",
        },
        "courses": {
            type: "courses",
            entry_point: "stats-api:stats_admission_campaign_exam_score_by_course",
        }
    };

    constructor(id, options) {
        super();
        this.id = id;
        this.templates = options.templates || {};

        this.state = {
            type: this.constructor.PLOT_TYPES.universities.type,
            campaignId: options.campaignId,
            data: {
                type: 'bar',
                keys: {
                    x: "score",
                    value: [],
                },
                // names: {
                //     total: i18n.total
                // },
                json: [],
                order: null, // https://github.com/c3js/c3/issues/1945
                unload: true
            }
        };

        this.plot = c3.generate({
            bindto: '#' + this.id,
            oninit: () => {
                this.appendOptionsForm()
            },
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
                        return this.plot.category(x) + i18n.score_suffix;
                    },
                }
            },
            data: this.state.data
        });

        this.fetchAndReflow(this.state.campaignId);
    }

    fetchAndReflow(campaignId) {
        this.getStats(campaignId)
            .then(this.convertData)
            .done(this.reflow);
    }

    getStats(campaignId) {
        // TODO: cache query
        let url = this.constructor.PLOT_TYPES[this.state.type].entry_point;
        let dataURL = URLS[url](campaignId);
        return $.getJSON(dataURL);
    }

    convertData = (json) => {
        if (json.length > 0) {
            const {score, ...values} = json[0];
            this.state.data.keys.value = Object.keys(values);
        }
        this.state.data.json = json;
        return json;
    };

    reflow = (json) => {
        this.plot.groups([this.state.data.keys.value]);
        this.plot.load(this.state.data);
        return json;
    };

    getOptions = () => {
        let data = [
            this.getPlotTypeOptionData(),
            {
                isSubmitButton: true,
                // FIXME: move template compilation to SubmitButtonMixin
                template: this.templates.submitButton,
                options: {value: "Выбрать"}
            }
        ];
        return data;
    };

    submitButtonHandler = () => {
        let newState = $(`#${this.id}-select`).val();
        if (newState !== this.state.type &&
            newState in this.constructor.PLOT_TYPES) {
            this.state.type = this.constructor.PLOT_TYPES[newState].type;
            // this.state.data.keys.x = this.constructor.PLOT_TYPES[newState].x_axis;
            this.fetchAndReflow(this.state.campaignId);
        }
        return false;
    };
}
