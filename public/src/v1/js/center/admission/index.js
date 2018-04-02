import initApplicantSection from './applicant';
import initInterviewSection from './interview';


$(document).ready(function () {
    let sections = $("body").data("init-sections").split(",");
    if (sections.includes("applicant")) {
        initApplicantSection();
    }
    if (sections.includes("interview")) {
        initInterviewSection();
    }
});