import {restoreTabFromHash} from './utils';
import {createNotification} from 'utils';
import _groupBy from 'lodash-es/groupBy';


function streamSelectChanged(event) {
    const streamSelect = event.target;
    let streamValues = Array(...streamSelect.options).reduce((acc, option) => {
        if (option.selected === true) {
            acc.push(parseInt(option.value));
        }
        return acc;
    }, []);
    const slotSelect = $("select[name='interview_from_stream-slot']");
    slotSelect.prop("disabled", "disabled");
    slotSelect.empty();
    if (streamValues.length > 0) {
        $.ajax({
            dataType: "json",
            url: window.URLS["admission-api:v2:interview_slots"],
            data: {
                streams: streamValues,
            },
        }).done((slots) => {
            let options = document.createDocumentFragment();
            let option = document.createElement('option');
            option.text = "Отправить приглашение на email";
            option.value = "";
            options.appendChild(option);
            let optGroups = _groupBy(slots, 'stream');
            Object.keys(optGroups).forEach((group) => {
                let optGroup = document.createElement('optgroup');
                optGroup.label = group;
                optGroups[group].forEach((slot) => {
                    let option = document.createElement('option');
                    let title;
                    if (slot.interview_id !== null) {
                        option.disabled = true;
                        title = `${slot.start_at} (занято)`;
                    } else {
                        title = `${slot.start_at}`;
                    }
                    option.text = title;
                    option.value = slot.id;
                    optGroup.appendChild(option);
                });
                options.appendChild(optGroup);
            });
            slotSelect.append(options);
            slotSelect.prop("disabled", false);
            slotSelect.selectpicker('refresh');
        }).fail(function (xhr) {
            createNotification(xhr, 'error');
        });
    }
}


export default function initApplicantDetailSection() {
    restoreTabFromHash();

    import('forms')
        .then(_ => {
            let streamSelect = $("select[name=interview_from_stream-streams]");
            streamSelect.selectpicker({
                actionsBox: true,
                iconBase: 'fa',
                tickIcon: 'fa-check'
            });
            streamSelect.on('loaded.bs.select', function (e) {
                $(e.target).selectpicker('setStyle', 'btn-default');
            });
            streamSelect.on('changed.bs.select', streamSelectChanged);
            let slotSelect = $("select[name=interview_from_stream-slot]");
            slotSelect.selectpicker({
                actionsBox: true,
            });
        });
}