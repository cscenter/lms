import {getOptionByValue} from "./Select";
import _isFunction from "lodash-es/isFunction";

/**
 * Common handler for input, select, radio buttons, multiple checkboxes
 * @param {Array<function(<Object>, name, value): Object>} applyPatches - Chain of callbacks which mutates the initial patch (order is matter)
 * @param {function(): void} setStateCallback - second argument for React `setState`
 * @param {string} name - state attribute name
 * @param {Object|Function} value - state value associated with the `name` attribute
 */
function onFilterChange({
                            applyPatches = null,
                            setStateCallback = undefined
                        } = {}, name, value) {
    this.setState((state) => {
        let v = _isFunction(value) ? value(state) : value;
        const patch = {
            [name]: v
        };
        if (applyPatches !== null) {
            for (const applyPatch of applyPatches) {
                Object.assign(patch, applyPatch.call(this, {...state, ...patch}));
            }
        }
        return patch;
    }, setStateCallback);
}


/**
 * @param {Object} callbacks - see `onFilterChange` for details
 * @returns {function(*): void} `onChange` state handler
 */
export function onRadioFilterChange(callbacks) {
    let partial = onFilterChange.bind(this, callbacks);
    return (event) => {
        const {name, value} = event.target;
        const optionsPropName = `${name}Options`;
        let option = getOptionByValue(this.props[optionsPropName], value);
        return partial(name, option);
    };
}


/**
 * Handle state for multiple checkboxes with the same name
 * @param {Object} callbacks - see `onFilterChange` for details
 * @returns {function(*): void} `onChange` state handler
 */
export function onMultipleCheckboxFilterChange(callbacks) {
    let partial = onFilterChange.bind(this, callbacks);
    return (event) => {
        const {name, value, checked} = event.target;
        let selectedCheckboxes = function(prevState) {
            let selected = [...prevState[name]] || [];
            if (checked === true) {
                selected.push(value);
            } else {
                let valueIndex = selected.indexOf(value);
                selected.splice(valueIndex, 1);
            }
            return selected;
        };
        return partial(name, selectedCheckboxes);
    };
}


export function onSelectFilterChange(callbacks) {
    let partial = onFilterChange.bind(this, callbacks);
    // `react-select` pass in (option, name) as arguments instead of react event
    return (option, name) => {
        return partial(name, option);
    };
}


/**
 * Handle state for multiple checkboxes with the same name
 */
export function onMultipleCheckboxChange(event, {applyPatch = null} = {}) {
    const {name, value, checked} = event.target;
    this.setState((state) => {
        let selectedCheckboxes = state[name] || [];
        if (checked === true) {
            selectedCheckboxes.push(value);
        } else {
            let valueIndex = selectedCheckboxes.indexOf(value);
            selectedCheckboxes.splice(valueIndex, 1);
        }
        const patch = {
            [name]: selectedCheckboxes
        };
        if (applyPatch !== null) {
            Object.assign(patch, applyPatch({...state, ...patch}));
        }
        return patch;
    });
}


/**
 * Handle state for SearchInput component
 * @param value {string} Query
 * @param name {string} input name
 * @param patchFn {Object}
 */
export function onSearchInputChange(value, name,
                                    {applyPatch = null} = {}) {
    this.setState((state) => {
        const patch = {
            [name]: value
        };
        if (applyPatch !== null) {
            Object.assign(patch, applyPatch({...state, ...patch}));
        }
        return patch;
    });
}

/**
 * Handle state for input
 * @param event - React event
 * @param {Array<function(<Object>, name, value): Object>} applyPatches - Chain of callbacks which mutates the initial patch (order is matter)
 * @param {function(): void} setStateCallback - second argument for `setState`
 */
export function onInputChange(event,
                              {applyPatches = null,
                              setStateCallback = undefined} = {}) {
    const target = event.target;
    const value = target.type === 'checkbox' ? target.checked : target.value;
    const name = target.name;
    this.setState((state) => {
        const patch = {
            [name]: value
        };
        if (applyPatches !== null) {
            for (const applyPatch of applyPatches) {
                Object.assign(patch, applyPatch({...state, ...patch}));
            }
        }
        return patch;
    }, setStateCallback);
}

/**
 * Handle state for react-select component
 * @param option {Object.<value, label>} Selected
 * @param name {string} select name attribute value
 */
// FIXME: нельзя менять состояние связанного селекта :<
export function onSelectChange(option,
                               name,
                               {
                                   applyPatch = null,
                                   setStateCallback = undefined
                               } = {}) {
    this.setState((state) => {
        const patch = {
            [name]: option
        };
        if (applyPatch !== null) {
            Object.assign(patch, applyPatch({...state, ...patch}));
        }
        return patch;
    }, setStateCallback);
}
