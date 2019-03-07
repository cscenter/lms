import React, {Fragment} from 'react';

import $ from 'jquery';
import PropTypes from 'prop-types';
import {hideBodyPreloader, showErrorNotification} from "utils";
import Select from "components/Select";
import Input from "components/Input";
import Checkbox from "components/Checkbox";
import RadioGroup from 'components/RadioGroup';
import RadioOption from 'components/RadioOption';


class ApplicationFormPage extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            "loading": true,
            ...props.initialState
        };
    }

    componentDidMount = () => {
        this.setState({loading: false})
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

    handleCourseChange = (option) => {
        this.setState({
            course: option
        });
    };

    handleUniversityChange = (university) => {
        this.setState({
            university: university
        });
    };

    render() {
        const {universities, courses, campaigns, study_programs, sources} = this.props;
        return (
            <form>
                <fieldset>
                    <h3>Личная информация</h3>
                    <div className="row">
                        <div className="field col-lg-4">
                            <label htmlFor="surname">Фамилия</label>
                            <Input name="surname" id="surname" onChange={this.handleInputChange} />
                        </div>

                        <div className="field col-lg-4">
                            <label htmlFor="first_name">Имя</label>
                            <Input name="first_name" id="first_name" onChange={this.handleInputChange} />
                        </div>

                        <div className="field col-lg-4">
                            <label htmlFor="patronymic">Отчество</label>
                            <Input name="patronymic" id="patronymic" onChange={this.handleInputChange} />
                        </div>

                        <div className="field col-lg-4">
                            <label htmlFor="email">Электронная почта</label>
                            <Input name="email" id="email" onChange={this.handleInputChange} />
                        </div>

                        <div className="field col-lg-4">
                            <label htmlFor="phone">Телефон</label>
                            <Input name="phone" id="phone" placeholder="+7" onChange={this.handleInputChange} />
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
                                https://stepik.org/users/XXXX, XXXX - это ваш ID
                            </div>
                        </div>
                        <div className="field col-lg-4">
                            <label htmlFor="github_id">Логин на GitHub</label>
                            <Input name="github_id" id="github_id" placeholder="ХХХХ" onChange={this.handleInputChange} />
                            <div className="help-text">
                                https://github.com/XXXX, логин — это XXXX
                            </div>
                        </div>
                        <div className="field col-lg-4">
                            <label>Доступ к данным на Яндексе</label>
                            <div className="grouped inline">
                                <Checkbox label="Разрешить доступ" />
                            </div>
                        </div>
                    </div>
                </fieldset>
                <fieldset>
                    <h3>Образование и опыт</h3>
                    <div className="row">
                        <div className="field col-lg-4">
                            <div className="ui select">
                                <label htmlFor="">Университет</label>
                                <Select
                                    onChange={this.handleUniversityChange}
                                    name="university"
                                    isClearable={true}
                                    placeholder="Выбрать из списка"
                                    options={universities}
                                    menuPortalTarget={document.body}
                                />
                            </div>
                            <div className="help-text">
                                Университет (и иногда факультет), в котором вы учитесь или который закончили
                            </div>
                        </div>
                        <div className="field col-lg-4">
                            <label htmlFor="">Факультет, специальность или кафедра</label>
                            <Input name="faculty" id="faculty" placeholder="" onChange={this.handleInputChange} />
                        </div>
                        <div className="field col-lg-4">
                            <div className="ui select">
                                <label htmlFor="">Курс</label>
                                <Select
                                    onChange={this.handleCourseChange}
                                    name="course"
                                    isClearable={true}
                                    placeholder="Выбрать из списка"
                                    options={courses}
                                    menuPortalTarget={document.body}
                                />
                            </div>
                        </div>
                    </div>
                    <div className="row">
                        <div className="field col-lg-12">
                            <label>Вы сейчас работаете?</label>
                            <RadioGroup name="work" className="inline">
                                <RadioOption id="yes">Да</RadioOption>
                                <RadioOption id="no">Нет</RadioOption>
                            </RadioGroup>
                        </div>
                    </div>
                    <div className="row">
                        <div className="field col-lg-8">
                            <div className="ui input">
                                <label>Расскажите об опыте программирования и исследований</label>
                                <p className="text-small mb-2">
                                    Напишите здесь о том, что вы делаете на работе, и о своей нынешней дипломной или курсовой работе.
                                    Здесь стоит рассказать о студенческих проектах, в которых вы участвовали, или о небольших личных проектах,
                                    которые вы делаете дома для своего удовольствия
                                </p>
                                <textarea name="experience" rows="6" onChange={this.handleInputChange} />
                            </div>
                        </div>
                        <div className="field col-lg-8">
                            <div className="ui input">
                                <label>Вы проходили какие-нибудь онлайн-курсы? Какие? Какие удалось закончить?</label>
                                <p className="text-small mb-2">Приведите ссылки на
                                    курсы или их названия и платформы,
                                    где вы их проходили. Расскажите о возникших
                                    трудностях. Что понравилось,
                                    а что не понравилось в таком формате
                                    обучения?
                                </p>
                                <textarea name="online_education_experience" rows="6" onChange={this.handleInputChange} />
                            </div>
                        </div>
                    </div>
                </fieldset>
                <fieldset>
                    <h3>Обучение в центре</h3>
                    <div className="row">
                        <div className="field col-lg-12">
                            <label>Выберите отделение, в котором собираетесь учиться</label>
                            <RadioGroup name="campaign" className="inline">
                                {campaigns.map((branch) =>
                                    <RadioOption key={branch.value} id={`campaign-${branch.value}`} value={branch.value}>
                                        {branch.label}
                                    </RadioOption>
                                )}
                            </RadioGroup>
                        </div>
                    </div>
                    <div className="row">
                        <div className="field col-8">
                            <label>Какие направления  обучения из трех вам интересны в CS центре?</label>
                            <p className="text-small mb-2">Мы не просим поступающих сразу определиться с направлением обучения.
                                Вам предстоит сделать этот выбор через год-полтора после поступления.
                                Сейчас мы предлагаем указать одно или несколько направлений, скажутся вам интересными.
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
                                <textarea name="motivation" rows="6" onChange={this.handleInputChange} />
                            </div>
                        </div>
                        <div className="field col-lg-8">
                            <label>Что нужно для выпуска из CS центра? Оцените вероятность, что вы сможете это сделать.</label>
                            <div className="ui input">
                                <textarea name="probability" rows="6" onChange={this.handleInputChange} />
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
                        <div className="field col-8">
                            <label>Какие направления  обучения из трех вам интересны в CS центре?</label>
                            <p className="text-small mb-2">Мы не просим поступающих сразу определиться с направлением обучения.
                                Вам предстоит сделать этот выбор через год-полтора после поступления.
                                Сейчас мы предлагаем указать одно или несколько направлений, скажутся вам интересными.
                            </p>
                            <div className="grouped">
                                {sources.map((source) =>
                                    <Checkbox
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
                    <p>Нажимая «Подать заявку», вы соглашаетесь на передачу данных CS центру и на получение писем по поводу приемной компании.</p>
                    <button className="btn _primary _m-wide">Подать заявку</button>
                </div>
            </form>
        );
    }
}

ApplicationFormPage.propTypes = {
    endpoint: PropTypes.string.isRequired,
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
