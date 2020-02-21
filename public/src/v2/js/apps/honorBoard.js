import 'bootstrap/js/src/tooltip';
import $ from 'jquery';

export function launch() {
    let achievementGrid = window.achievementGrid;
    if (achievementGrid !== "undefined") {
        let studentAchievements = {};
        Object.keys(achievementGrid).forEach((code) => {
            let students = achievementGrid[code];
            students.forEach((userId) => {
                studentAchievements[userId] = studentAchievements[userId] || [];
                studentAchievements[userId].push(code);
            });
        });
        Object.keys(studentAchievements).forEach((userId) => {
            let codes = studentAchievements[userId];
            let wrapper = document.createElement("div");
            wrapper.className = "achievements";
            codes.forEach((code) => {
                let div = document.createElement('div');
                div.className = "achievements__item";
                div.setAttribute("data-toggle", "tooltip");
                div.setAttribute("title", window.ACHIEVEMENTS[code]);
                div.innerHTML = `<svg class="sprite-img _${code}" xmlns:xlink="http://www.w3.org/1999/xlink"><use xlink:href="#${code}"></use></svg>`;
                wrapper.appendChild(div);
            });
            document.querySelector(`#user-card-${userId} .card__img`).appendChild(wrapper);
        });
        $('[data-toggle="tooltip"]').tooltip({
            animation: false,
            placement: "auto",
            delay: {"show": 100, "hide": 0}
        }).click(function (e) {
            e.preventDefault();
        });

    }
}