import SelectBase from 'react-select';
import PropTypes from 'prop-types';
import React from 'react';


const inputStyles = {
    input: styles => ({
        ...styles,
        margin: 0,
        paddingBottom: 0,
        paddingTop: 0,
    }),
};


class SelectLazy extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            optionsLoaded: false,
            options: [],
            isLoading: false
        }
    }

    handleChange = (e) => {
        this.props.onChange(e);
    };

    maybeLoadOptions = () => {
        if (!this.state.optionsLoaded) {
            this.setState({isLoading: true});
            this.props.handleLoadOptions(this);
        }
    };

    render() {
        return (
            <SelectBase
                name={this.props.name}
                value={this.props.value}
                clearable={false}
                className='react-select-container'
                classNamePrefix='react-select'
                styles={inputStyles}
                {...this.props}
                onChange={this.handleChange}
                isLoading={this.state.isLoading}
                options={this.state.options}
                onFocus={this.maybeLoadOptions}
                isSearchable={true}
            />
        );
    }
}

SelectLazy.propTypes = {
    onChange: PropTypes.func.isRequired,
    handleLoadOptions: PropTypes.func.isRequired
};

export default SelectLazy;
