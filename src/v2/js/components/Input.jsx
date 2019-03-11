import _isNil from 'lodash-es/isNil';
import React from 'react';
import PropTypes from 'prop-types';


class Input extends React.Component {
    static defaultProps = {
        type: 'text',
        className: ''
    };

    computeTabIndex = () => {
        const {disabled, tabIndex} = this.props;

        if (!_isNil(tabIndex)) {
            return tabIndex;
        }
        if (disabled) {
            return -1;
        }
    };

    render() {
        const {
            className,
            ...rest
        } = this.props;
        const tabIndex = this.computeTabIndex();
        // FIXME remove handleChange if disabled?
        // FIXME: do not hardcode autoComplete
        return (
            <div className={`ui input ${className}`}>
                <input
                    tabIndex={tabIndex}
                    autoComplete="off"
                    {...rest}
                />
            </div>
        );
    }
}

Input.propTypes = {
    onChange: PropTypes.func,
    type: PropTypes.string,
    tabIndex: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    value: PropTypes.string,
    /** An Input field can show a user is currently interacting with it. */
    focus: PropTypes.bool,
    /** Additional classes. */
    className: PropTypes.string,
    disabled: PropTypes.bool,
};

export default Input;