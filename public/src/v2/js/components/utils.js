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
 */
export function onInputChange(event,
                              {applyPatch = null,
                              setStateCallback = undefined} = {}) {
    const target = event.target;
    const value = target.type === 'checkbox' ? target.checked : target.value;
    const name = target.name;

    this.setState((state) => {
        const patch = {
            [name]: value
        };
        if (applyPatch !== null) {
            Object.assign(patch, applyPatch({...state, ...patch}));
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
                               name, {
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
