import React from 'react';
import * as PropTypes from 'prop-types';
import cx from 'classnames';
import RadioGroupContext from './RadioGroupContext';

function RadioGroup(props) {
    const {
        className = '',
        value = null,
        onChange = null,
        disabled = false,
        required = null,
        name,
        children,
    } = props;
    return (
        <RadioGroupContext.Provider value={{selected: value, onChange, name, required, groupDisabled: disabled}}>
            <div className={cx("grouped", className)} role="radiogroup">
                {children}
            </div>
        </RadioGroupContext.Provider>
    );
}

RadioGroup.propTypes = {
    children: PropTypes.node.isRequired,
    inputRef: PropTypes.func,
    required: PropTypes.bool,
    name: PropTypes.string.isRequired,
    /**
     * Value of the selected radio button. The DOM API casts this to a string.
     */
    value: PropTypes.any,
    onChange: PropTypes.func,
    disabled: PropTypes.bool,
    className: PropTypes.string,
};

export default RadioGroup;
