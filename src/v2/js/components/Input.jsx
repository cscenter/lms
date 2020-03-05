import _isNil from 'lodash-es/isNil';
import React from 'react';
import PropTypes from 'prop-types';
import classNames from 'classnames';

function computeTabIndex(disabled, tabIndex) {
    if (disabled) {
        return -1;
    }
    if (!_isNil(tabIndex)) {
        return tabIndex;
    }
}


const Input = React.forwardRef(function Input(props, ref) {
    const {type = 'text', autoComplete = 'off', className = '', disabled = false, tabIndex = null, ...rest} = props;
    const computedTabIndex = computeTabIndex(disabled, tabIndex);
    let wrapperClass = classNames({
        'ui input': true,
        [className]: className.length > 0,
        'disabled': disabled
    });
    return (
        <div className={wrapperClass}>
            <input
                tabIndex={computedTabIndex}
                autoComplete={autoComplete}
                type={type}
                ref={ref}
                disabled={disabled}
                {...rest}
            />
        </div>
    );

});

Input.propTypes = {
    onChange: PropTypes.func,
    type: PropTypes.string,
    tabIndex: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    value: PropTypes.string,
    /** An Input field can show a user is currently interacting with it. */
    focus: PropTypes.bool,
    /** Additional classes. */
    className: PropTypes.string,
    autoComplete: PropTypes.string,
    disabled: PropTypes.bool,
};

export default Input;