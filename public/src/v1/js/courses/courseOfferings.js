import {getTemplate, showComponentError} from 'utils';

const MESSAGES = {
    term: 'Семестр: ',
};

// TODO: add assert for `window.courseOfferingsData`


function courseOfferingsList() {
    const wrapper = document.getElementById('courses-list');
    if (wrapper === null) return;
    // Filters
    const yearsFilter = $('.__courses-filter--academic-year');
    const termsFilter = $('.__courses-filter--term');
    let eventData = {
        yearsFilter: yearsFilter,
        termsFilter: termsFilter,
        offeringsData: window.courseOfferingsData,
        templates: {
            courseRow: getTemplate('courses-list-table-row'),
            termOption: getTemplate('courses-term-filter-option')
        }
    };
    yearsFilter.on('change', 'select[name="academic_year"]', eventData,
        filterCourseOfferings);
    termsFilter.on('click', 'a', eventData,
        filterTermAction);
    // Tooltips
    $(wrapper).tooltip({
        // Internally use `$().on` if `selector` provided
        selector: '.__club, .__image, .__file, .__video'
    });
    // Restore filter
    window.onpopstate = function(event) {
        let filterState;
        if (event.state !== null) {
            if ('filterState' in event.state) {
                filterState = event.state.filterState;
            }
        }
        if (filterState === undefined) {
            filterState = eventData.offeringsData.initialFilterState;
        }
        updateDOM(eventData, filterState.termSlug, filterState.academicYear,
            filterState.selectedTerm);
    };
}

function filterTermAction(event) {
    event.preventDefault();
    if ($(this).hasClass('active')) return;

    event.data.termsFilter.find('a').removeClass('active');
    $(this).addClass('active');
    filterCourseOfferings(event);
}

function filterCourseOfferings(event) {
    event.preventDefault();
    let currentCity = event.data.offeringsData.branch;
    let academicYear = parseInt(event.data.yearsFilter.find('select').val());
    let selectedTerm = event.data.termsFilter.find('.active').data("type");
    let year = academicYear;
    if (selectedTerm === 'spring') {
        year += 1;
    }
    // Make sure termType available for selected year
    let slug = `${year}-${selectedTerm}`;
    if (!(slug in event.data.offeringsData.courses)) {
        let availableTerms = event.data.offeringsData.terms[academicYear];
        year = academicYear;
        // Note: terms in reversed order
        selectedTerm = availableTerms[availableTerms.length - 1];
        if (selectedTerm === 'spring') {
            year += 1;
        }
        slug = `${year}-${selectedTerm}`;
    }
    if (slug in event.data.offeringsData.courses) {
        updateDOM(event.data, slug, academicYear, selectedTerm);
        // Update history
        if (!!(window.history && history.pushState)) {
            let path = `${location.protocol}//${location.host}${location.pathname}`;
            let href = `${path}?branch=${currentCity}&semester=${slug}`;
            history.pushState(
                {
                    filterState: {
                        termSlug: slug,
                        academicYear: academicYear,
                        selectedTerm: selectedTerm
                    }
                },
                "",
                href
            );
        }
    } else {
        // throw an error? Should be impossible.
    }
}

function updateDOM(eventData, termSlug, academicYear, selectedTerm) {
    let availableTerms = eventData.offeringsData.terms[academicYear];
    // Update table content
    let rows = "";
    eventData.offeringsData.courses[termSlug].forEach((course) => {
        rows += eventData.templates.courseRow({co: course});
    });
    $('.__courses tbody').html(rows);
    // Update term types list
    let termOptions = availableTerms.reduceRight((acc, termType) => {
        acc += eventData.templates.termOption({
            activeType: selectedTerm,
            term: {
                type: termType,
                name: eventData.offeringsData.termOptions[termType]
            }
        });
        return acc;
    }, MESSAGES.term);
    eventData.termsFilter.html(termOptions);
    // Update select value. Need it for browser history
    eventData.yearsFilter.find('select').val(academicYear);
}


export function launch() {
    courseOfferingsList();
    import('components/forms')
        .then(m => {
            $('.__courses-filter--academic-year select').selectpicker({
                showTick: false,
                iconBase: 'fa',
                tickIcon: 'fa-check',
                width: 'fit',
            });
        })
        .catch(error => showComponentError(error));
}

