import React from 'react';
import PropTypes from 'prop-types';
import Icon from "./Icon";

function InputIcon(props) {
    const icon = props.icon;
    if (icon !== null) {
        return (
            <i className={`_${icon} icon`}>
                <Icon id={icon}/>
            </i>
        );
    }

    return null;
}

class SearchInput extends React.Component {
    static defaultProps = {
        value: ''
    };

    handleChange = (e) => {
        this.props.onChange(e.target.value);
    };

    render() {
        const {icon} = this.props;
        const iconClass = icon !== null ? "icon" : "";
        return (
            <div className={`ui ${iconClass} input`}>
                <input
                    name="query"
                    type="text"
                    autoComplete="off"
                    {...this.props}
                    onChange={this.handleChange}
                />
                <InputIcon icon={icon}/>
            </div>
        );
    }
}

SearchInput.propTypes = {
    onChange: PropTypes.func.isRequired,
    value: PropTypes.string.isRequired
};

export default SearchInput;