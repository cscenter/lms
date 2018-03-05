function toggleUniversity() {
    $('select[name$="-university"]').change(function () {
        var universityID = parseInt(this.value);
        // Hide additional field if selected `Other`
        var disabled = (universityID !== 10 && universityID !== 14);
        if (disabled) {
            $('#university-other-row').addClass('hidden');
        } else {
            $('#university-other-row')
                .removeClass('hidden')
                .find('input').focus();
        }
    });
}

function toggleHasJob() {
    $('input[name$="-has_job"]').change(function () {
        const disabled = this.value !== 'yes';
        console.log(disabled);
        if (disabled) {
            $('#job-details-row').addClass('hidden');
        } else {
            $('#job-details-row')
                .removeClass('hidden')
                .find('input[name$="-workplace"]').focus();
        }
    });
}

function toggleStudyProjects() {
    $('input[name$="-preferred_study_programs"]').change(function () {
        const code = this.value;
        let $textarea = $('textarea[name$=-preferred_study_programs_' + code + '_note]');
        if ($(this).is(':checked')) {
            $textarea.closest('.col-sm-12').removeClass('hidden');
        } else {
            $textarea.closest('.col-sm-12').addClass('hidden');
        }
    })
}

function toggleWhereDidYouLearn() {
    $('input[name$="-where_did_you_learn"]').change(function () {
        if (this.value !== 'other') {
            return;
        }
        let $textarea = $('input[name$=-where_did_you_learn_other]');
        if ($(this).is(':checked')) {
            $textarea.closest('.col-sm-12').removeClass('hidden');
            $textarea.focus();
        } else {
            $textarea.closest('.col-sm-12').addClass('hidden');
        }
    })
}

export function initApplicationForm() {
    toggleUniversity();
    toggleHasJob();
    toggleStudyProjects();
    toggleWhereDidYouLearn();
}