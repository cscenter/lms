function toggleUniversity() {
    $('select[name$="-university"]').change(function () {
        var universityID = parseInt(this.value);
        // FIXME: What the magic constants?
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
    $('select[name$="-has_job"]').change(function () {
        const disabled = this.value !== 'yes';
        $('input[name$="-workplace"]').prop('disabled', disabled);
        $('input[name$="position"]').prop('disabled', disabled);

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
        } else {
            $textarea.closest('.col-sm-12').addClass('hidden');
        }
    })
}

function showStepBackWarning() {
    $('.__prev-step').click(function (e) {
        // TODO: Check form was changed
        e.preventDefault();
        swal({
            title: "",
            text: "Данные текущего шага будут утеряны",
            type: "warning",
            showCancelButton: true,
            confirmButtonClass: "btn-danger",
            cancelButtonText: "Отмена!",
            confirmButtonText: "Продолжить"
        }, function (isConfirm) {
            if (isConfirm) {
                window.location.href = this.href;
            } else {
                return false;
            }
        });
    });
}

export function initApplicationForm() {
    toggleUniversity();
    toggleHasJob();
    toggleStudyProjects();
    toggleWhereDidYouLearn();
    showStepBackWarning();
}