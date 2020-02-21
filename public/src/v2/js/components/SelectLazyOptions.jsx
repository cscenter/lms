import SelectBase from 'react-select';
import * as PropTypes from 'prop-types';
import React from 'react';
import {selectOptionType} from 'types/props';


const inputStyles = {
    input: styles => ({
        ...styles,
        margin: 0,
        paddingBottom: 0,
        paddingTop: 0,
    }),
};


class SelectLazyOptions extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            optionsLoaded: false,
            options: [],
            isLoading: false
        };
    }

    handleChange = (e) => {
        this.props.onChange(e, this.props.name);
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

SelectLazyOptions.propTypes = {
    name: PropTypes.string.isRequired,
    value: selectOptionType,
    onChange: PropTypes.func.isRequired,
    handleLoadOptions: PropTypes.func.isRequired
};

export default SelectLazyOptions;
