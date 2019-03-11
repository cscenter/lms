import React, {Fragment} from 'react';

import 'bootstrap/js/src/tooltip';
import $ from 'jquery';
import PropTypes from 'prop-types';
import {showNotification, showErrorNotification} from "utils";
import Select from "components/Select";
import {Creatable as CreatableSelect} from 'react-select';
import Input from "components/Input";
import Checkbox from "components/Checkbox";
import RadioGroup from 'components/RadioGroup';
import RadioOption from 'components/RadioOption';
import {SelectDefaultProps} from "components/Select";


class ApplicationFormPage extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            "loading": true,
            ...props.initialState
        };
    }

    componentDidMount = () => {
        this.setState({loading: false});
        // Yandex.Passport global handlers (postMessage could be broken in IE11-)
        window.accessYandexLoginSuccess = (login) => {
            this.setState({isYandexPassportAccessAllowed: true});
            showNotification("Доступ успешно предоставлен", {type: "success"});
        };
        window.accessYandexLoginError = function(msg) {
            showNotification(msg, {type: "error"});
        };
        $('[data-toggle="tooltip"]').tooltip();
    };

    componentWillUnmount = function () {
        this.serverRequest.abort();
    };

    componentDidUpdate(prevProps, prevState) {

    };

    openAuthPopup = function(url) {
        const width = 700;
        const height = 600;
        const leftOffset = 100;
        const topOffset = 100;

        url += `?next=${this.props.authCompleteUrl}`;
        let name = "";
        const settings = `height=${height},width=${width},left=${leftOffset},top=${topOffset},resizable=yes,scrollbars=yes,toolbar=no,menubar=no,location=yes,directories=no,status=yes`;
        window.open(url, name, settings);
    };

    handleInputChange = (event) => {
        const target = event.target;
        const value = target.type === 'checkbox' ? target.checked : target.value;
        const name = target.name;

        this.setState({
            [name]: value
        });
    };

    /**
     * Handle state for multiple checkboxes with the same name
     * @param event
     */
    handleMultipleCheckboxChange = (event) => {
        const {name, value} = event.target;
        let selectedCheckboxes = this.state[name] || [];
        if (event.target.checked === true) {
            selectedCheckboxes.push(value);
        } else {
            let valueIndex = selectedCheckboxes.indexOf(value);
            selectedCheckboxes.splice(valueIndex, 1);
        }
        this.setState({
            [name]: selectedCheckboxes
        });
    };

    handleUniversityChange = (university) => {
        this.setState({
            university: university
        });
    };


    handleCourseChange = (option) => {
        this.setState({
            course: option
        });
    };

    handleAccessYandexLogin = (event) => {
        event.preventDefault();
        const {isYandexPassportAccessAllowed} = this.state;
        if (isYandexPassportAccessAllowed) {
            return false;
        }
        this.openAuthPopup(this.props.authBeginUrl);
        return false;
    };

    handleSubmit = e => {
        e.preventDefault();
        const {endpoint, csrfToken, campaigns} = this.props;
        const {has_job, university, course, campaign, ...payload} = this.state;
        payload["course"] = course && course.value;
        payload["has_job"] = (has_job === "yes");
        if (university) {
            if (university.__isNew__) {
                payload["university_other"] = university.value;
            } else {
                payload["university"] = university.value;
            }
        }
        let campaignSelectedOption = campaigns.find(obj => {
            return obj.value === campaign
        });
        payload["campaign"] = campaignSelectedOption.id;

        this.serverRequest = $.ajax({
            url: endpoint,
            type: "post",
            headers: {
                'X-CSRFToken': csrfToken
            },
            dataType: "json",
            contentType: 'application/json',
            data: JSON.stringify(payload)
        }).done((data) => {
            this.setState({isFormSubmitted: true});
        }).fail((jqXHR) => {
            if (jqXHR.status === 400) {
                let msg = "<h5>Анкета не была сохранена</h5>";
                const data = jqXHR.responseJSON;
                if (Object.keys(data).length === 1 &&
                        data.hasOwnProperty('non_field_errors')) {
                    msg += data['non_field_errors'];
                    showErrorNotification(msg);
                } else {
                    msg += "Все поля обязательны для заполнения.";
                    showNotification(msg, {type: "error", timeout: 3000});
                }
            } else {
                showErrorNotification("Что-то пошло не так. Попробуйте позже.")
            }
        });
    };

    render() {
        const {universities, courses, campaigns, studyPrograms, sources} = this.props;
        const {
            isYandexPassportAccessAllowed,
            has_job,
            where_did_you_learn,
            campaign,
            preferred_study_programs,
            isFormSubmitted,
        } = this.state;

        let filteredStudyPrograms = studyPrograms.filter((program) => {
            if (campaign === "nsk") {
                return program.value !== "cs";
            }
            return true;
        });

        if (isFormSubmitted) {
            return (
                <Fragment>
                <h3>Заявка зарегистрирована</h3>
                Спасибо за интерес к обучению в CS центре.<br/>
                В ближайшее время вам придёт письмо с дальнейшими инструкциями и ссылкой на тест для поступающих.<br/>
                Если в течение суток письмо не пришло, поищите его в спаме. Если там нет, напишите на <a href="mailto:info@compscicenter.ru">info@compscicenter.ru</a> о своей проблеме. Не забудьте указать свои ФИО и email.
                </Fragment>
            );
        }

        return (
            <form className="ui form" onSubmit={this.handleSubmit}>
                <fieldset>
                    <h3>Личная информация</h3>
                    <div className="row">
                        <div className="field col-lg-4">
                            <label htmlFor="surname">Фамилия</label>
                            <Input required name="surname" id="surname" onChange={this.handleInputChange} />
                        </div>

                        <div className="field col-lg-4">
                            <label htmlFor="first_name">Имя</label>
                            <Input required name="first_name" id="first_name" onChange={this.handleInputChange} />
                        </div>

                        <div className="field col-lg-4">
                            <label htmlFor="patronymic">Отчество</label>
                            <Input name="patronymic" id="patronymic" onChange={this.handleInputChange} />
                        </div>

                        <div className="field col-lg-4">
                            <label htmlFor="email">Электронная почта</label>
                            <Input type="email" required name="email" id="email" onChange={this.handleInputChange} />
                        </div>

                        <div className="field col-lg-4">
                            <label htmlFor="phone">Контактный телефон</label>
                            <Input required name="phone" id="phone" placeholder="+7 (999) 1234567" onChange={this.handleInputChange} />
                        </div>
                    </div>
                </fieldset>
                <fieldset>
                    <h3>Аккаунты</h3>
                    <div className="row">
                        <div className="field col-lg-4">
                            <label htmlFor="stepic_id">ID на Stepik.org</label>
                            <Input name="stepic_id" id="stepic_id" placeholder="ХХХХ" onChange={this.handleInputChange} />
                            <div className="help-text">
                                https://stepik.org/users/xxxx, ID — это xxxx
                            </div>
                        </div>
                        <div className="field col-lg-4">
                            <label htmlFor="github_id">Логин на GitHub</label>
                            <Input name="github_id" id="github_id" placeholder="ХХХХ" onChange={this.handleInputChange} />
                            <div className="help-text">
                                https://github.com/xxxx, логин — это xxxx
                            </div>
                        </div>
                        <div className="field col-lg-4 mb-2">
                            <label>
                                Доступ к данным на Яндексе&nbsp;
                                <span
                                    className="tooltip__icon"
                                    data-toggle="tooltip"
                                    data-placement="bottom"
                                    title="Вступительный тест организован в системе Яндекс.Контест. Чтобы выдать права участника и затем сопоставить результаты с анкетами, нам нужно знать ваш логин на Яндексе без ошибок, учитывая все особенности, например, вход через социальные сети. Чтобы всё сработало, поделитесь с нами доступом к некоторым данным из вашего Яндекс.Паспорта: логин и ФИО."
                                >?</span>
                            </label>
                            <div className="grouped inline">
                                <Checkbox
                                    required
                                    label={isYandexPassportAccessAllowed ? "Доступ разрешен" : "Разрешить доступ"}
                                    disabled={isYandexPassportAccessAllowed}
                                    checked={isYandexPassportAccessAllowed}
                                    onChange={() => {}}
                                    onClick={this.handleAccessYandexLogin}
                                />
                            </div>
                        </div>
                    </div>
                </fieldset>
                <fieldset>
                    <h3>Образование и опыт</h3>
                    <div className="row">
                        <div className="field col-lg-4">
                            <div className="ui select">
                                <label htmlFor="">Вуз</label>
                                <CreatableSelect
                                    required
                                    {...SelectDefaultProps}
                                    isClearable={true}
                                    onChange={this.handleUniversityChange}
                                    name="university"
                                    placeholder="---"
                                    options={universities}
                                    menuPortalTarget={document.body}
                                />
                            </div>
                            <div className="help-text">
                                Выберите из списка или введите название вуза, где вы учитесь или учились
                            </div>
                        </div>
                        <div className="field col-lg-4">
                            <label htmlFor="faculty">Факультет</label>
                            <Input required name="faculty" id="faculty" placeholder="" onChange={this.handleInputChange} />
                            <div className="help-text">
                                Факультет, специальность или кафедра
                            </div>
                        </div>
                        <div className="field col-lg-4">
                            <div className="ui select">
                                <label htmlFor="">Курс</label>
                                <Select
                                    required
                                    onChange={this.handleCourseChange}
                                    name="course"
                                    isClearable={true}
                                    placeholder="---"
                                    options={courses}
                                    menuPortalTarget={document.body}
                                />
                            </div>
                        </div>
                    </div>
                    <div className="row">
                        <div className="field col-lg-12 mb-2">
                            <label>Вы сейчас работаете?</label>
                            <RadioGroup required name="has_job" className="inline" onChange={this.handleInputChange}>
                                <RadioOption id="yes">Да</RadioOption>
                                <RadioOption id="no">Нет</RadioOption>
                            </RadioGroup>
                        </div>
                    </div>
                    {
                        has_job && has_job === "yes" &&
                            <div className="row ">
                                <div className="field col-lg-4">
                                    <label htmlFor="position">Должность</label>
                                    <Input name="position" id="position" placeholder="" onChange={this.handleInputChange} />
                                </div>
                                <div className="field col-lg-4">
                                    <label htmlFor="workplace">Место работы</label>
                                    <Input name="workplace" id="workplace" placeholder="" onChange={this.handleInputChange} />
                                </div>
                            </div>
                    }
                    <div className="row">
                        <div className="field col-lg-8">
                            <div className="ui input">
                                <label htmlFor="experience">Расскажите об опыте программирования и исследований</label>
                                <p className="text-small mb-2">
                                    Напишите здесь о том, что вы делаете на работе, и о своей нынешней дипломной или курсовой работе. Здесь стоит рассказать о студенческих проектах, в которых вы участвовали, или о небольших личных проектах, которые вы делаете дома, для своего удовольствия. Если хотите, укажите ссылки, где можно посмотреть текст или код работ.
                                </p>
                                <textarea id="experience" name="experience" rows="6" onChange={this.handleInputChange} />
                            </div>
                        </div>
                        <div className="field col-lg-8">
                            <div className="ui input">
                                <label htmlFor="online_education_experience">Вы проходили какие-нибудь онлайн-курсы? Какие? Какие удалось закончить?</label>
                                <p className="text-small mb-2">
                                    Приведите ссылки на курсы или их названия и платформы, где вы их проходили. Расскажите о возникших трудностях. Что понравилось, а что не понравилось в таком формате обучения?
                                </p>
                                <textarea id="online_education_experience" name="online_education_experience" rows="6" onChange={this.handleInputChange} />
                            </div>
                        </div>
                    </div>
                </fieldset>
                <fieldset>
                    <h3>CS центр</h3>
                    <div className="row">
                        <div className="field col-lg-12 mb-2">
                            <label>Выберите отделение, в котором собираетесь учиться</label>
                            <RadioGroup required name="campaign" className="inline" onChange={this.handleInputChange}>
                                {campaigns.map((branch) =>
                                    <RadioOption  key={branch.value} id={`campaign-${branch.value}`} value={branch.value}>
                                        {branch.label}
                                    </RadioOption>
                                )}
                            </RadioGroup>
                        </div>
                    </div>
                    {
                        campaign && (campaign === "spb" || campaign === "nsk") &&
                        <Fragment>
                            <div className="row">
                                <div className="field col-lg-8">
                                    <label>Какие направления  обучения из трех вам интересны в CS центре?</label>
                                    <p className="text-small mb-2">
                                        Мы не просим поступающих сразу определиться с направлением обучения. Вам предстоит сделать этот выбор через год-полтора после поступления. Сейчас мы предлагаем указать одно или несколько направлений, которые кажутся вам интересными.
                                    </p>
                                    <div className="grouped">
                                        {filteredStudyPrograms.map((studyProgram) =>
                                            <Checkbox
                                                name="preferred_study_programs"
                                                key={studyProgram.value}
                                                value={studyProgram.value}
                                                onChange={this.handleMultipleCheckboxChange}
                                                label={studyProgram.label}
                                            />
                                        )}
                                    </div>
                                </div>
                            </div>
                            {
                                preferred_study_programs && preferred_study_programs.includes('cs') &&
                                <div className="field col-lg-8">
                                    <div className="ui input">
                                        <label htmlFor="preferred_study_programs_cs_note">Вы бы хотели заниматься исследованиями в области Computer Science? Какие темы вам особенно интересны?</label>
                                        <p className="text-small mb-2">
                                            Вы можете посмотреть список возможных тем и руководителей НИРов у нас на <a target="_blank" href="https://compscicenter.ru/pages/projects/#research-curators">сайте</a>.
                                        </p>
                                        <textarea id="preferred_study_programs_cs_note" name="preferred_study_programs_cs_note" rows="6" onChange={this.handleInputChange} />
                                    </div>
                                </div>
                            }
                            {
                                preferred_study_programs && preferred_study_programs.includes('ds') &&
                                <div className="field col-lg-8">
                                    <div className="ui input">
                                        <label htmlFor="preferred_study_programs_dm_note">Что вам больше всего интересно в области Data Science? Какие достижения последних лет вас особенно удивили?</label>
                                        <textarea id="preferred_study_programs_dm_note" name="preferred_study_programs_dm_note" rows="6" onChange={this.handleInputChange} />
                                    </div>
                                </div>
                            }
                            {
                                preferred_study_programs && preferred_study_programs.includes('se') &&
                                <div className="field col-lg-8">
                                    <div className="ui input">
                                        <label htmlFor="preferred_study_programs_se_note">В разработке какого приложения, которым вы пользуетесь каждый день, вы хотели бы принять участие? Каких знаний вам для этого не хватает?</label>
                                        <textarea id="preferred_study_programs_se_note" name="preferred_study_programs_se_note" rows="6" onChange={this.handleInputChange} />
                                    </div>
                                </div>
                            }
                        </Fragment>
                    }
                    {
                        campaign && campaign === "online" &&
                        <div className="row">
                            <div className="field col-lg-5">
                                <Input required name="living_place" id="living_place" placeholder="В каком городе вы живёте?" onChange={this.handleInputChange} />
                            </div>
                        </div>
                    }

                    <div className="row">
                        <div className="field col-lg-8">
                            <label>Почему вы хотите учиться в CS центре? Что вы ожидаете от обучения?</label>
                            <div className="ui input">
                                <textarea required name="motivation" rows="6" onChange={this.handleInputChange} />
                            </div>
                        </div>
                        <div className="field col-lg-8">
                            <label>Что нужно для выпуска из CS центра? Оцените вероятность, что вы сможете это сделать</label>
                            <div className="ui input">
                                <textarea required name="probability" rows="6" onChange={this.handleInputChange} />
                            </div>
                        </div>
                        <div className="field col-lg-8">
                            <label>Напишите любую дополнительную информацию о себе</label>
                            <div className="ui input">
                                <textarea name="additional_info" rows="6" onChange={this.handleInputChange} />
                            </div>
                        </div>
                    </div>
                    <div className="row">
                        <div className="field col-lg-8">
                            <label className="mb-4">Откуда вы узнали о CS центре?</label>
                            <div className="grouped">
                                {sources.map((source) =>
                                    <Checkbox
                                        key={source.value}
                                        name="where_did_you_learn"
                                        value={source.value}
                                        onChange={this.handleMultipleCheckboxChange}
                                        label={source.label}
                                    />
                                )}
                            </div>
                        </div>
                        {
                            where_did_you_learn && where_did_you_learn.includes("other") &&
                            <div className="field animation col-lg-5">
                                <Input required name="where_did_you_learn_other" placeholder="Ваш вариант" onChange={this.handleInputChange} />
                            </div>
                        }
                    </div>
                </fieldset>
                <div className="row">
                    <div className="col-lg-12">
                        <p>Нажимая «Подать заявку», вы соглашаетесь на передачу данных CS центру и на получение писем по поводу приемной кампании.</p>
                        <button type="submit" className="btn _primary _m-wide">Подать заявку</button>
                    </div>
                </div>
            </form>
        );
    }
}

ApplicationFormPage.propTypes = {
    endpoint: PropTypes.string.isRequired,
    authBeginUrl: PropTypes.string.isRequired,
    authCompleteUrl: PropTypes.string.isRequired,
    campaigns: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired
    })).isRequired,
    universities: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.number.isRequired,
        label: PropTypes.string.isRequired,
        city_id: PropTypes.string.isRequired
    })).isRequired,
    courses: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired,
    })).isRequired,
    studyPrograms: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired,
    })).isRequired
};


export default ApplicationFormPage;
