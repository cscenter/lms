const _debounce = require('lodash/debounce');

const ENTRY_POINT = $('.user-search #ajax-uri').val();
let queryName = "";
let cities = {};
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

            let selectedCities = Object.keys(cities)
                .filter(key => cities[key])
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
                    cities: selectedCities,
                    curriculum_year: selectedYears,
                    groups: selectedGroups,
                    status: selectedStatuses,
                    cnt_enrollments: selectedEnrollmentsCount,
                },
                dataType: "json",
                traditional: true
            }).done(function (msg) {
                const numStr = msg.users.length.toString() + (msg.there_is_more ? "+" : "");
                $("#user-num-container").show();
                $("#user-num").text(numStr);
                let h = "<table class='table table-condensed'>";
                msg.users.map((user) => {
                    h += "<tr><td><a href=\"" + user.url + "\">";
                    h += user.last_name + " " + user.first_name;
                    h += "</a></td></tr>";
                });
                if (msg.there_is_more) {
                    h += "<tr><td>…</td></tr>";
                }
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
            .on('input paste', '#name', function (e) {
                queryName = $(this).val();
                query();
            })
            .on('change', '[name="cities"]', function (e) {
                cities[$(this).val()] = this.checked;
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
