
export function getSections() {
    if (document.body.hasAttribute("data-init-sections")) {
        let sections = document.body.getAttribute("data-init-sections");
        return sections.split(",");
    } else {
        return [];
    }
}

export function showComponentError(error, msg='An error occurred while loading the component') {
    console.error(error);
    alert(error);  // TODO: add jGrowl or something similar
}