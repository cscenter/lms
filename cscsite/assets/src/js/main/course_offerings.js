import {getTemplate} from 'utils';

// Maybe need to translate those strings in the future.
const MESSAGES = {
    tooltip_club: 'Курс CS клуба',
    video: 'Видео',
    files: 'Файлы',
    slides: 'Слайды'
};


export default function courseOfferingsList() {
    const wrapper = document.getElementById('courses-list');
    if (wrapper === null) return;
    // init filters
    const yearsFilter = $('.__courses-filter--academic-year');
    const termsFilter = $('.__courses-filter--term');
    let eventData = {
        yearsFilter: yearsFilter,
        termsFilter: termsFilter,
        offeringsData: window.courseOfferingsData,
        courseRowTemplate: getTemplate('courses-list-table-row'),
        termOptionTemplate: getTemplate('courses-term-filter-option')
    };
    yearsFilter.on('change', 'select[name="academic_year"]', eventData,
        filterCourseOfferings);
    termsFilter.on('click', 'a', eventData,
        filterTermAction);
    $(wrapper).tooltip({
        // Internally use `$().on` if `selector` provided
        selector: '.__club, .__image, .__file, .__video'
    });
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
    let academicYear = parseInt(event.data.yearsFilter.find('select').val());
    let selectedTerm = event.data.termsFilter.find('.active').data("type");
    let year = academicYear;
    if (selectedTerm === 'spring') {
        year += 1;
    }
    // Make sure termType available for selected year
    let slug = `${year}-${selectedTerm}`;
    let availableTerms = event.data.offeringsData.terms[academicYear];
    if (!(slug in event.data.offeringsData.courses)) {
        year = academicYear;
        // Note: terms in reversed order
        selectedTerm = availableTerms[availableTerms.length - 1];
        if (selectedTerm === 'spring') {
            year += 1;
        }
        slug = `${year}-${selectedTerm}`;
    }
    if (slug in event.data.offeringsData.courses) {
        // Update table content
        let rows = "";
        event.data.offeringsData.courses[slug].forEach((course) => {
            rows += event.data.courseRowTemplate({co: course});
        });
        $('.__courses-test tbody').html(rows);
        // Update term types list
        let termOptions = availableTerms.reduceRight((acc, termType) => {
            acc += event.data.termOptionTemplate({
                activeType: selectedTerm,
                term: {
                    type: termType,
                    name: event.data.offeringsData.termOptions[termType]
                }
            });
            return acc;
        }, "Семестр: ");
        event.data.termsFilter.html(termOptions);
    } else {
        // throw an error? Should be impossible.
    }
    // Pick available term and update term types list
}