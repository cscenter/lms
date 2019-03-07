import React, {Fragment} from 'react';

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
        }
    };

    componentWillUnmount = function () {
        this.serverRequest.abort();
    };

    componentDidUpdate(prevProps, prevState) {

    };

    handleInputChange = (event) => {
        const target = event.target;
        const value = target.type === 'checkbox' ? target.checked : target.value;
        const name = target.name;

        this.setState({
            [name]: value
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

    handleAccessYandexLogin = (event) => {
        event.preventDefault();
        const {isYandexPassportAccessAllowed} = this.state;
        if (isYandexPassportAccessAllowed) {
            return false;
        }
        this.openAuthPopup(this.props.authBeginUrl);
        return false;
    };

    render() {
        const {isYandexPassportAccessAllowed} = this.state;
        const {universities, courses, campaigns, study_programs, sources} = this.props;
        return (
            <form className="ui form">
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
                            <Input required name="patronymic" id="patronymic" onChange={this.handleInputChange} />
                        </div>

                        <div className="field col-lg-4">
                            <label htmlFor="email">Электронная почта</label>
                            <Input required name="email" id="email" onChange={this.handleInputChange} />
                        </div>

                        <div className="field col-lg-4">
                            <label htmlFor="phone">Контактный телефон</label>
                            <Input required name="phone" id="phone" placeholder="+7" onChange={this.handleInputChange} />
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
                            <label>Доступ к данным на Яндексе</label>
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
                            <label htmlFor="faculty">Факультет, специальность или кафедра</label>
                            <Input required name="faculty" id="faculty" placeholder="" onChange={this.handleInputChange} />
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
                            <RadioGroup required name="has_job" className="inline">
                                <RadioOption id="yes">Да</RadioOption>
                                <RadioOption id="no">Нет</RadioOption>
                            </RadioGroup>
                        </div>
                    </div>
                    <div className="row">
                        <div className="field col-lg-6">
                            <label htmlFor="position">Должность</label>
                            <Input name="position" id="position" placeholder="" onChange={this.handleInputChange} />
                        </div>
                        <div className="field col-lg-6">
                            <label htmlFor="workplace">Место работы</label>
                            <Input name="workplace" id="workplace" placeholder="" onChange={this.handleInputChange} />
                        </div>
                    </div>
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
                        <div className="field col-lg-12">
                            <label>Выберите отделение, в котором собираетесь учиться</label>
                            <RadioGroup name="campaign" className="inline">
                                {campaigns.map((branch) =>
                                    <RadioOption required key={branch.value} id={`campaign-${branch.value}`} value={branch.value}>
                                        {branch.label}
                                    </RadioOption>
                                )}
                            </RadioGroup>
                        </div>
                    </div>
                    <div className="row">
                        <div className="field col-lg-8">
                            <label>Какие направления  обучения из трех вам интересны в CS центре?</label>
                            <p className="text-small mb-2">
                                Мы не просим поступающих сразу определиться с направлением обучения. Вам предстоит сделать этот выбор через год-полтора после поступления. Сейчас мы предлагаем указать одно или несколько направлений, которые кажутся вам интересными.
                            </p>
                            <div className="grouped">
                                {study_programs.map((study_program) =>
                                    <Checkbox
                                        key={study_program.value}
                                        value={study_program.value}
                                        checked={false}
                                        onChange={this.handleInputChange}
                                        label={study_program.label}
                                    />
                                )}
                            </div>
                        </div>
                    </div>
                    <div className="row">
                        <div className="field col-lg-8">
                            <label>Почему вы хотите учиться в CS центре? Что вы ожидаете от обучения?</label>
                            <div className="ui input">
                                <textarea required name="motivation" rows="6" onChange={this.handleInputChange} />
                            </div>
                        </div>
                        <div className="field col-lg-8">
                            <label>Что нужно для выпуска из CS центра? Оцените вероятность, что вы сможете это сделать.</label>
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
                                        required
                                        key={source.value}
                                        name="where_did_you_learn"
                                        value={source.value}
                                        checked={false}
                                        onChange={this.handleInputChange}
                                        label={source.label}
                                    />
                                )}
                            </div>
                        </div>
                    </div>
                </fieldset>
                <div className="row">
                    <div className="col-lg-12">
                        <p>Нажимая «Подать заявку», вы соглашаетесь на передачу данных CS центру и на получение писем по поводу приемной компании.</p>
                        <button type="button" className="btn _primary _m-wide">Подать заявку</button>
                        <button type="submit" className="btn _primary _m-wide">test</button>
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
        value: PropTypes.number.isRequired,
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
    study_programs: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired,
    })).isRequired
};


export default ApplicationFormPage;
