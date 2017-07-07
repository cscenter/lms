let template = require('lodash.template');

export function getTemplate (id) {
    return template(document.getElementById(id).innerHTML);
}

export const GROUPS = {
    1: "Студент центра",
    4: "Вольнослушатель",
    3: "Выпускник",
};
