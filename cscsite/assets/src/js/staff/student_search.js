(function ($, _) {
    "use strict";

    var enrollmentYears = {};
    var groups = {};
    var status = {};
    var qstr = "";
    var cnt_enrollments = {};
    var ajaxURI = $('.user-search #ajax-uri').val();

    var fn = {
        launch: function () {
            var query = function () {
                var flatYears,
                    flatGroups,
                    flatStatuses,
                    flatEnrollmentsCount;

                flatYears = _.chain(enrollmentYears)
                    .pairs()
                    .filter(function (x) {
                        return x[1]
                    })
                    .map(function (x) {
                        return x[0]
                    })
                    .value().join(",");
                flatStatuses = _.chain(status)
                    .pairs()
                    .filter(function (x) {
                        return x[1]
                    })
                    .map(function (x) {
                        return x[0]
                    })
                    .value().join(",");
                flatEnrollmentsCount = _.chain(cnt_enrollments)
                    .pairs()
                    .filter(function (x) {
                        return x[1]
                    })
                    .map(function (x) {
                        return x[0]
                    })
                    .value().join(",");
                flatGroups = _.chain(groups)
                    .pairs()
                    .filter(function (x) {
                        return x[1]
                    })
                    .map(function (x) {
                        return x[0]
                    })
                    .value();

                $.ajax({
                    url: ajaxURI,
                    data: {
                        name: qstr,
                        enrollment_year: flatYears,
                        groups: flatGroups,
                        status: flatStatuses,
                        cnt_enrollments: flatEnrollmentsCount,
                    },
                    dataType: "json",
                    traditional: true
                }).done(function (msg) {
                    var numStr = (msg.users.length.toString()
                    + (msg.there_is_more ? "+" : ""));

                    $("#user-num-container").show();
                    $("#user-num").text(numStr);
                    var h = "<table class=\"table table-condensed\">";
                    _.each(msg.users, function (user) {
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
            query = _.debounce(query, 200);

            $('.user-search [name="enrollment_year_cb"]')
                .each(function (idx, obj) {
                    enrollmentYears[$(obj).val()] = false;
                });

            $('.user-search')
                .on('input paste', '#name', function (e) {
                    qstr = $(this).val();
                    query();
                })
                .on('change', '[name="enrollment_year_cb"]', function (e) {
                    enrollmentYears[$(this).val()] = this.checked;
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

    $(document).ready(function () {
        fn.launch();
    });

})(jQuery, _);