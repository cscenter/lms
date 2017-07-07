import getTemplate from 'stats/utils';

// DOM elements
let cityFilter = $('#city-filter');
let campaignFilter = $('#campaign-filter');
let campaignFilterForm = $('#campaigns-filter-form');

 function renderPlots (campaignID) {
     return;
}

function initFilter() {
    campaignFilter.on('change', function () {
        $('button[type=submit]', campaignFilterForm).removeAttr('disabled');
    });
    // TODO: refactor
    cityFilter.on('change', function () {
        const cityCode = $(this).val();
        const items = json_data.campaigns[cityCode];
        campaignFilter.empty();
        items.forEach(function (item) {
            let opt = document.createElement('option');
            opt.value = item['pk'];
            opt.innerHTML = item['year'];
            campaignFilter.get(0).appendChild(opt);
        });
        campaignFilter.selectpicker('refresh');
        $('button[type=submit]', campaignFilterForm).removeAttr('disabled');
    });
}

function initPlots() {
    const id = json_data.campaign;
    initFilter();
    renderPlots(id);
}

module.exports = {
     init: initPlots
};
