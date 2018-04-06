import initApplicantDetailSection from './applicant_detail';
import initApplicantListSection from './applicant_list';
import initInterviewSection from './interview';


$(document).ready(function () {
    let sections = $("body").data("init-sections").split(",");
    if (sections.includes("applicant_list")) {
        initApplicantListSection();
    }
    if (sections.includes("applicant")) {
        initApplicantDetailSection();
    }
    if (sections.includes("interview")) {
        initInterviewSection();
    }
});