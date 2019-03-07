import _isNil from 'lodash-es/isNil';
import React from 'react';
import PropTypes from 'prop-types';
import Input from "./Input";


class Checkbox extends React.Component {
    static defaultProps = {
        className: '',
    };

    constructor(props) {
        super(props);
        this.state = {checked: false};
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

    handleClick = (e) => {
        this.setState({checked: !this.state.checked});
    };

    handleChange = (e) => {
        this.props.onChange(e.target.value);
    };

    render() {
        const {
            className,
            label,
            ...rest
        } = this.props;
        const { checked } = this.state;
        const tabIndex = this.computeTabIndex();
        return (
            <label className={`ui option ${className}`}>
                <input
                    className="control__input"
                    checked={checked}
                    tabIndex={tabIndex}
                    onChange={this.handleChange}
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