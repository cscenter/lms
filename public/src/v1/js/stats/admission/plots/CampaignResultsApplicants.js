import * as d3 from "d3";
import c3 from "c3";
import $ from 'jquery';
import {URLS} from 'stats/utils';
import i18n from 'stats/i18n';
import mix from 'stats/MixinBuilder';
import PlotOptions from "stats/PlotOptions";
import {COLOR_PALETTE} from "stats/utils";
import PlotTypeOptionMixin from "./PlotTypeOptionMixin";


export default class CampaignResultsApplicants extends mix(PlotOptions).with(PlotTypeOptionMixin) {
    static PLOT_TYPES = {
        "universities": {
            type: "universities",
            entry_point: "stats-api:stats_admission_campaign_applicants_by_university",
            x_axis: "university__name"
        },
        "courses": {
            type: "courses",
            entry_point: "stats-api:stats_admission_campaign_applicants_by_course",
            x_axis: "course__name"
        }
    };

    constructor(id, options) {
        super();
        this.id = id;
        this.templates = options.templates || {};

        let values = [
            "accept",
            "accept_if",
            "volunteer",
            "rejected_interview",
            "they_refused",
        ];
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
                names: i18n.statuses,
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
                pattern: COLOR_PALETTE
            },
            bindto: '#' + this.id,
            oninit: () => {
                this.appendOptionsForm()
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
        this.state.data.json = json;
        return json;
    };

    reflow = (json) => {
        this.plot.load(this.state.data);
        return json;
    };

    getOptions = () => {
        let data = [
            this.getPlotTypeOptionData(),
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
            this.fetchAndReflow(this.state.campaignId);
        }
        return false;
    };
}
