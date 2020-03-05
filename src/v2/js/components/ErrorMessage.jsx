import React from 'react';
import {ErrorMessage as BaseErrorMessage} from "react-hook-form";
import PropTypes from 'prop-types';


function ErrorMessage({className = '', ...rest}) {
    return (
        <BaseErrorMessage {...rest}>
            {({messages, message}) => {
                let errors = message ? [message] : messages;
                return (
                    errors &&
                    <p className={`help-text error ${className}`}>
                        {Object.entries(errors).map(([type, message]) => (
                            <span key={type}>{message}</span>
                        ))}
                    </p>
                );
            }}
        </BaseErrorMessage>
    );
}

ErrorMessage.propTypes = {
    className: PropTypes.string
};

export default ErrorMessage;