/**
 * Handle state for multiple checkboxes with the same name
 * @param event
 */
export function onMultipleCheckboxChange(event) {
    const {name, value} = event.target;
    let selectedCheckboxes = this.state[name] || [];
    if (event.target.checked === true) {
        selectedCheckboxes.push(value);
    } else {
        let valueIndex = selectedCheckboxes.indexOf(value);
        selectedCheckboxes.splice(valueIndex, 1);
    }
    this.setState({
        [name]: selectedCheckboxes
    });
}


/**
 * Handle state for SearchInput component
 * @param value {string} Query
 * @param name {string} input name
 */
export function onSearchInputChange(value, name) {
    this.setState({
        [name]: value
    });
}

/**
 * Handle state for input
 * @param event
 */
export function onInputChange(event) {
    const target = event.target;
    const value = target.type === 'checkbox' ? target.checked : target.value;
    const name = target.name;

    this.setState({
        [name]: value
    });
}

/**
 * Handle state for input
 * @param event
 */
export function onInputChangeLoading(event) {
    const target = event.target;
    const value = target.type === 'checkbox' ? target.checked : target.value;
    const name = target.name;
    // FIXME: combine with onInputChange
    this.setState(state => {
        return {
            [name]: value,
            loading: state[name] !== value
        }
    });
}

/**
 * Handle state for react-select component
 * @param option {Object.<value, label>} Selected
 * @param name {string} select name attribute value
 */
export function onSelectChange(option, name) {
    this.setState({
        [name]: option
    });
}


/**
 * Handle state for react-select component.
 * Set `loading` flag to true if a new value differ from previous
 * @param option {Object.<value, label>} Selected
 * @param name {string} select name attribute value
 */
export function onSelectChangeLoading(option, name) {
    this.setState(state => {
        return {
            [name]: option,
            loading: state[name] !== option
        }
    });
}
