import React from 'react';
import {ErrorMessage, Input} from "components";
import PropTypes from 'prop-types';
import {refType} from 'types/props';
import classNames from 'classnames';


const fieldProps = {
    inputRef: refType,
    className: PropTypes.string,
    name: PropTypes.string.isRequired,
    label: PropTypes.string,
    helpText: PropTypes.string,
    wrapperClass: PropTypes.string,
    errors: PropTypes.object,
};


export function InputField({className = '', wrapperClass = '', helpText = '', name, label, errors = null, inputRef, ...rest}) {
    return (
        <div className={`field ${wrapperClass}`}>
            {label && <label htmlFor={name}>{label}</label>}
            <Input name={name}
                   id={name}
                   className={errors && errors[name] ? `${className} error`: className}
                   ref={inputRef}
                   {...rest} />
            {helpText && <div className="help-text">{helpText}</div>}
            {errors && <ErrorMessage errors={errors} name={name} />}
        </div>
    );
}

InputField.propTypes = fieldProps;


export function TextField({className = '', wrapperClass = '', helpText = '', name, label, errors = null, inputRef, ...rest}) {

    let inputClass = classNames({
        'ui input': true,
        'error': errors && errors[name],
    });

    return (
        <div className={`field ${wrapperClass}`}>
            {label && <label htmlFor={name}>{label}</label>}
            {helpText && <div className="text-small mb-2">{helpText}</div>}
            <div className={inputClass}>
                <textarea name={name}
                          id={name}
                          rows="6"
                          ref={inputRef}
                          {...rest} />
            </div>
            {errors && <ErrorMessage errors={errors} name={name} />}
        </div>
    );
}

TextField.propTypes = fieldProps;


export const MemoizedInputField = React.memo(InputField);

export const MemoizedTextField = React.memo(TextField);
