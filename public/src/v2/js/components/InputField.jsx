import React from 'react';
import {ErrorMessage, Input} from "components";
import PropTypes from 'prop-types';


function InputField({className = '', wrapperClass = '', helpText = '', name, label, errors, ...rest}) {
    return (
        <div className={`field ${wrapperClass}`}>
            {label && <label htmlFor={name}>{label}</label>}
            <Input name={name}
                   id={name}
                   className={errors[name] ? `${className} error`: className}
                   {...rest} />
            {helpText && <div className="help-text">{helpText}</div>}
            <ErrorMessage errors={errors} name={name} />
        </div>
    );
}

InputField.propTypes = {
    className: PropTypes.string,
    name: PropTypes.string.isRequired,
    label: PropTypes.string,
    helpText: PropTypes.string,
    wrapperClass: PropTypes.string,
    errors: PropTypes.object,
};

export default InputField;