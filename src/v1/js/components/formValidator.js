export class FormValidation {
    constructor(form, isValidCallback, isInvalidCallback) {
        this.form = form;
        this.submitButton = form.querySelector('[type="submit"]');
        this.isValidCallback = isValidCallback;
        this.isInvalidCallback = isInvalidCallback;
        this.onSubmitFormHandler = this.onSubmitFormHandler.bind(this);
        this.submitButton.addEventListener('click', this.onSubmitFormHandler);
    }

    onSubmitFormHandler(e) {
        e.preventDefault();
        let encodedProperties = [];
        this.form.elements.forEach((field) => {
            if (field.name) {
                let encodedField = `${encodeURIComponent(field.name)}=${encodeURIComponent(field.value)}`;
                encodedProperties.push(encodedField);
            }
        });
        this.validateForm(encodedProperties.join('&'));
    }

    validateForm(data) {
        $.ajax({
            method: "PUT",
            url: this.form.getAttribute('action'),
            contentType: 'application/x-www-form-urlencoded',
            dataType: "json",
            data: data,
        })
            .done((data) => {
                this.clearErrorMessages();
                this.isValidCallback(this.form, data);
                // $('#assignee-value').text(assigneeName);
            })
            .fail((jqXHR) => {
                let errors = JSON.parse(jqXHR.responseText);
                this.clearErrorMessages();
                this.applyErrorMessages(errors);
                this.isInvalidCallback(this.form, errors);
                // createNotification('kek', 'error');
            });
    }

    clearErrorMessages() {
        let errors = this.form.querySelectorAll('.error-message');
        if (errors.length) {
            [...errors].map(error => {
                const formGroup = error.closest('.form-group');
                if (formGroup !== null) {
                    formGroup.classList.remove('has-error');
                }
                error.remove();
            });
        }
    }

    applyErrorMessages(data) {
        for (let fieldName in data) {
            if (fieldName === 'non_field_errors') {
                this._handleNonFieldErrors(data[fieldName]);
            } else {
                this._handleFieldErrors(data[fieldName], fieldName);
            }
        }
    }

    _handleNonFieldErrors(errors) {
        let anchorPoint = this.form.querySelector('.non_field_errors');
        for (let i=0; i < errors.length; i++) {
            let error = errors[i];
            anchorPoint.appendChild(this._newError(` - ${error}`));
        }
    }

    _handleFieldErrors(errors, fieldName) {
        let field = this.form.querySelector(`[name="${fieldName}"]`);
        if (field) {
            // Loop over any error messages.
            for (let i=0; i < errors.length; i++) {
                field.closest('.form-group').append(this._newError(errors[i]));
                field.closest('.form-group').classList.add('has-error');
            }
        }
    }

    _newError(content) {
        let div = document.createElement('div');
        div.className = 'error-message';
        div.appendChild(document.createTextNode(content));
        return div;
    }
}