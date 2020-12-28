import {showComponentError} from 'utils';
import { query, toEnhancedHTMLElement } from "@drivy/dom-query";
import {createNotification} from "../utils";
import {FormValidation} from "components/formValidator";

const fn = {
    launch: function () {
        fn.initAssigneeForm();
        import('components/forms')
            .then(m => {
                m.initSelectPickers();
            })
            .catch(error => showComponentError(error));
    },

    initAssigneeForm: function () {
        const modalFormWrapper = $("#update-assignee-form");
        modalFormWrapper.modal({
            show: false
        });

        new FormValidation(
            modalFormWrapper.find('form').get(0),
            function (form, data) {
                let assigneeId = data.assignee;
                if (assigneeId === null) {
                    assigneeId = '';
                }
                const selectedAssigneeOption = toEnhancedHTMLElement(form).query(`select[name="assignee"] option[value="${assigneeId}"]`);
                $('#assignee-value').text(selectedAssigneeOption.text);
                createNotification('Изменения успешно сохранены');
                modalFormWrapper.modal('hide');
            }, function () {
                createNotification('Форма не сохранена. Попробуйте позже.', 'error');
            });
        modalFormWrapper.on('submit', 'form', function(e) {
            e.preventDefault();
            const form = e.target;
            const assigneeSelect = query('#assignee-select');
            const assigneeId = assigneeSelect.value;
            const assigneeName = assigneeSelect.options[assigneeSelect.selectedIndex].text;
            $.ajax({
                method: "PUT",
                url: form.getAttribute('action'),
                dataType: "json",
                data: {
                    assignee: assigneeId,
                },
            })
                .done((data) => {
                    $('#assignee-value').text(assigneeName);
                })
                .fail((xhr) => {
                    createNotification('kek', 'error');
                    console.log(xhr);
                });

        });
    },
};

export default fn;