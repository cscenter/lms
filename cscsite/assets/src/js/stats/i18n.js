const i18n = {
    pieChart: "Круговая",
    barChart: "Гистограмма",
    total: "Всего",
    total_participants: "Всего слушателей курса",
    people_suffix: "&nbsp;чел.",
    score_suffix: "&nbsp;баллов",
    groups: {
        STUDENT_CENTER: "Студент центра",
        VOLUNTEER: "Вольнослушатель",
        GRADUATE_CENTER: "Выпускник",
    },
    stages: {
        application_form: "Подача анкеты",
        testing: "Тестирование",
        examination: "Экзамен",
        interviewing: "Собеседование",
    },
    statuses: {
        accept: "Принят",
        accept_if: "Принят с условием",
        volunteer: "Берём в вольные слушатели",
        rejected_interview: "Отказ по результатам собеседования",
        they_refused: "Отказался",
        rejected_test: "",
        rejected_exam: "",
        interview_phase: "",
        rejected_cheating: "",
        interview_assigned: "",
        interview_completed: "",
    },
    assignments: {
        title: "Задания",
        participants: "Слушатели курса",
        passed: "Сдали задание",
        no_assignments: "Заданий не найдено.",
        lines: {
            pass: "Проходной балл",
            mean: "Средний балл",
            max: "Максимальный балл"
        },
    },
    submissions: {
        deadline_types: {
            gte7days: "7 дней и более",
            lte1to6days: "1-6 дней",
            lte3to24hours: "3-24 часа",
            lt3hours: "Менее 3 часов",
            after: "После дедлайна",
            // no_submission: "Не сдавал"
        },
        statuses: {
            not_submitted: "Не отправлено",
            not_checked: "Не проверено",
            unsatisfactory: "Незачет",
            pass: "Удовлетворительно",
            good: "Хорошо",
            excellent: "Отлично"
        },
    },
    enrollments: {
        no_enrollments: "Студенты не найдены.",
        grades: {
            not_graded: "Без оценки",
            unsatisfactory: "Незачет",
            pass: "Удовлетворительно",
            good: "Хорошо",
            excellent: "Отлично"
        }
    }
};

export default i18n;