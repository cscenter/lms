import _debounce from 'lodash-es/debounce';

const ENTRY_POINT = $('.user-search #ajax-uri').val();
let queryName = "";
let branches = {};
let curriculumYears = {};
let groups = {};
let status = {};
let cnt_enrollments = {};

const fn = {
    launch: function () {
        let query = function () {
            let selectedYears = Object.keys(curriculumYears)
                .filter(key => curriculumYears[key])
                .join(",");

            let selectedBranches = Object.keys(branches)
                .filter(key => branches[key])
                .join(",");

            let selectedStatuses = Object.keys(status)
                .filter(key => status[key])
                .join(",");

            let selectedEnrollmentsCount = Object.keys(cnt_enrollments)
                .filter(key => cnt_enrollments[key])
                .join(",");

            let selectedGroups = Object.keys(groups)
                .filter(key => groups[key])
                .join(",");

            $.ajax({
                url: ENTRY_POINT,
                data: {
                    name: queryName,
                    branches: selectedBranches,
                    curriculum_year: selectedYears,
                    groups: selectedGroups,
                    status: selectedStatuses,
                    cnt_enrollments: selectedEnrollmentsCount,
                },
                dataType: "json",
                traditional: true
            }).done(function (data) {
                let found;
                if (data.next !== null) {
                    found = `Показано: 500 из ${data.count}`;
                } else {
                    found = `Найдено: ${data.count}`;
                }
                $("#user-num-container").html(found).show();
                let h = "<table class='table table-condensed'>";
                data.results.map((user) => {
                    h += `<tr><td>`;
                    h += `<a href="/users/${user.pk}/">${user.short_name}</a>`;
                    h += "</td></tr>";
                });
                h += "</table>";
                $("#user-table-container").html(h);
            });
        };
        query = _debounce(query, 200);

        $('.user-search[name="curriculum_year_cb"]')
            .each(function (idx, obj) {
                curriculumYears[$(obj).val()] = false;
            });

        $('.user-search')
            .on("keydown", function (e) {
                // Supress Enter
                if (e.keyCode === 13) {
                    e.preventDefault();
                }
            })
            .on('input paste', '#name', function (e) {
                queryName = $(this).val();
                query();
            })
            .on('change', '[name="branches"]', function (e) {
                branches[$(this).val()] = this.checked;
                query();
            })
            .on('change', '[name="curriculum_year_cb"]', function (e) {
                curriculumYears[$(this).val()] = this.checked;
                query();
            })
            .on('change', '[name="group"]', function (e) {
                groups[$(this).val()] = this.checked;
                query();
            })
            .on('change', '[name="status"]', function (e) {
                status[$(this).val()] = this.checked;
                query();
            })
            .on('change', '[name="cnt_enrollments"]', function (e) {
                cnt_enrollments[$(this).val()] = this.checked;
                query();
            });
    },
};

$(function () {
    fn.launch();
});
