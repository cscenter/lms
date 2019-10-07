import CampaignStagesTimeline from "./plots/CampaignStagesTimeline";
import ApplicationFormSubmissionTimeline from "./plots/ApplicationFormSubmissionTimeline";
import ApplicantsResultsTimeline from "./plots/ApplicantsResultsTimeline";
import CampaignResultsStudents from "./plots/CampaignResultsStudents";
import CampaignTestScore from "./plots/CampaignTestScore";
import CampaignExamScore from "./plots/CampaignExamScore";
import CampaignStages from "./plots/CampaignStages";
import CampaignResultsApplicants from "./plots/CampaignResultsApplicants";
import {getTemplate} from "stats/utils";

// DOM elements
let branchFilter = $('#branch-filter');
let campaignFilter = $('#campaign-filter');
let campaignFilterForm = $('#campaigns-filter-form');

 function renderPlots (jsonData) {
    let options = {
        campaignId: jsonData.campaignId,
        branchId: jsonData.branchId,
        templates: {
            select: getTemplate("plot-filter-select-template"),
            submitButton: getTemplate("plot-filter-submit-button")
        },
    };
    // By branch
    new CampaignStagesTimeline('#plot-campaigns-stages-timeline', options);
    new ApplicationFormSubmissionTimeline('#plot-application-timeline', options);
    new ApplicantsResultsTimeline('#plot-applicants-results-timeline', options);
    // By admission campaign
    new CampaignStages('plot-campaign-stages', options);
    new CampaignResultsApplicants('plot-campaign-applicants-results', options);
    new CampaignTestScore('plot-campaign-testing-scores', options);
    new CampaignExamScore('plot-campaign-exam-scores', options);
    // new CampaignResultsStudents('#plot-campaign-students-results', options);
}

function initFilter() {
    campaignFilter.on('change', function () {
        $('button[type=submit]', campaignFilterForm).removeAttr('disabled');
    });
    branchFilter.on('change', function () {
        const branchId = $(this).val();
        const items = jsonData.campaigns[branchId];
        campaignFilter.empty();
        items.forEach(function (item) {
            let opt = document.createElement('option');
            opt.value = item.id;
            opt.innerHTML = item.year;
            campaignFilter.get(0).appendChild(opt);
        });
        campaignFilter.selectpicker('refresh');
        $('button[type=submit]', campaignFilterForm).removeAttr('disabled');
    });
}

export function initPlots() {
    initFilter();
    renderPlots(jsonData);
}