import {restoreTabFromHash} from './utils';

function interviewFromStreamForm() {
    const wrapper = $(".admission-applicant-page #create");
    wrapper.find("select[name=interview_from_stream-stream]")
        .change({wrapper: wrapper}, _interviewSlotsHandler);
}

function _interviewSlotsHandler(event) {
    const wrapper = event.data.wrapper;
    const streamSelect = wrapper.find("select[name=interview_from_stream-stream]");
    const slotSelect = wrapper.find("select[name='interview_from_stream-slot']");
    const streamID = parseInt(streamSelect.val());
    if (!isNaN(streamID)) {
        slotSelect
        // FIXME: По-хорошему надо запоминать предыдущее успешное состояние. Если оно не меняется - избегать запросов. datepicker должен ещё какое-то событие посылать, если значение не валидно и он выставляет сам предыдущее...
            .find('option')
            .remove();
        // TODO: Replace url with data from js_reverse?
        $.ajax({
            dataType: "json",
            url: "/admission/interviews/slots/",
            data: {
                stream: streamID,
            },
        }).done((data) => {
            slotSelect.append($('<option>').text("---------").attr('value', ""));
            data.forEach((slot) => {
                let title;
                if (slot.interview_id !== null) {
                    title = `${slot.start_at} (занято)`;
                } else {
                    title = `${slot.start_at}`;
                }
                slotSelect.append($('<option>')
                    .text(title)
                    .attr('value', slot.pk)
                    .prop('disabled', slot.interview_id !== null));
            });
        }).fail(function (xhr) {
            console.log(xhr);
        });
    }
}


export default function initApplicantDetailSection() {
    restoreTabFromHash();
    interviewFromStreamForm();
}