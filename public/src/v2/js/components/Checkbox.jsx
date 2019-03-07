import _isNil from 'lodash-es/isNil';
import React from 'react';
import classNames from 'classnames';
import PropTypes from 'prop-types';
import Input from "./Input";


class Checkbox extends React.Component {
    static defaultProps = {
        className: '',
        disabled: false,
        required: false
    };

    constructor(props) {
        super(props);
        this.state = {};
    }

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
            label,
            disabled,
            required,
            ...rest
        } = this.props;
        const tabIndex = this.computeTabIndex();

        let labelClass = classNames({
            'ui option checkbox': true,
            [className]: className.length > 0,
            'disabled': disabled
        });

        return (
            <label className={labelClass}>
                <input
                    type="checkbox"
                    required
                    className="control__input"
                    tabIndex={tabIndex}
                    {...rest}
                />
                <span className="control__indicator" />
                <span className="control__description">{label}</span>
            </label>
        );
    }
}

Checkbox.propTypes = {
    label: PropTypes.string.isRequired,
    checked: PropTypes.bool,
    onChange: PropTypes.func,
    tabIndex: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    value: PropTypes.string,
    /** Additional classes. */
    className: PropTypes.string,
    disabled: PropTypes.bool,
};

export default Checkbox;