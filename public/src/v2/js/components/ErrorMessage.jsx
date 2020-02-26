import React from 'react';
import {ErrorMessage as BaseErrorMessage} from "react-hook-form";


function ErrorMessage(props) {
    return (
        <BaseErrorMessage {...props}>
            {({messages, message}) => {
                let errors = message ? [message] : messages;
                return (
                    errors &&
                    <p className="help-text error">
                        {Object.entries(errors).map(([type, message]) => (
                            <span key={type}>{message}</span>
                        ))}
                    </p>);
            }}
        </BaseErrorMessage>
    );
}

export default ErrorMessage;