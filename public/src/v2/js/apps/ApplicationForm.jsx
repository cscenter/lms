import React, {Fragment, useReducer, useEffect} from 'react';
import ky from 'ky';
import * as PropTypes from 'prop-types';
import { useAsync } from "react-async";
import { useForm } from 'react-hook-form';

import {
    Checkbox,
    CreatableSelect,
    ErrorMessage,
    InputField,
    MemoizedTextField,
    Input,
    RadioGroup,
    RadioOption,
    Select,
    Tooltip
} from "components";
import {optionStrType} from "types/props";
import {showErrorNotification, showNotification} from "utils";


// TODO: потестить isPending. Есть какой-то devtools для react-async


const YandexAccessTooltip = () => (
    <Tooltip title="Вступительный тест организован в системе Яндекс.Контест. Чтобы выдать права участника и затем сопоставить результаты с анкетами, нам нужно знать ваш логин на Яндексе без ошибок, учитывая все особенности, например, вход через социальные сети. Чтобы всё сработало, поделитесь с нами доступом к некоторым данным из вашего Яндекс.Паспорта: логин и ФИО.">
        <span className="tooltip__icon _rounded">?</span>
    </Tooltip>
);


let openAuthPopup = function(url, authCompleteUrl) {
    const width = 700;
    const height = 600;
    const leftOffset = 100;
    const topOffset = 100;

    url += `?next=${authCompleteUrl}`;
    let name = "";
    const settings = `height=${height},width=${width},left=${leftOffset},top=${topOffset},resizable=yes,scrollbars=yes,toolbar=no,menubar=no,location=yes,directories=no,status=yes`;
    window.open(url, name, settings);
};


const submitForm = async ([endpoint, csrfToken, setState, payload], props, { signal }) => {
    const response = await ky.post(endpoint, {
        headers: {
            'X-CSRFToken': csrfToken
        },
        throwHttpErrors: false,
        json: payload,
        signal: signal
    });
    if (!response.ok) {
        if (response.status === 400) {
            const data = response.json();
            let msg = "<h5>Анкета не была сохранена</h5>";
            if (Object.keys(data).length === 1 &&
                    Object.prototype.hasOwnProperty.call(data, 'non_field_errors')) {
                msg += data['non_field_errors'];
                showErrorNotification(msg);
            } else {
                msg += "Одно или более полей пропущены или заполнены некорректно.";
                showNotification(msg, {type: "error", timeout: 3000});
            }
        } else if (response.status === 403) {
            let msg = "<h5>Анкета не была сохранена</h5>Приемная кампания окончена.";
            showErrorNotification(msg);
        } else {
            showErrorNotification("Что-то пошло не так. Попробуйте позже.");
        }
    } else {
        setState({isFormSubmitted: true});
    }
};


function ApplicationForm({
                             endpoint,
                             csrfToken,
                             authCompleteUrl,
                             authBeginUrl,
                             campaigns,
                             universities,
                             educationLevelOptions,
                             studyProgramOptions,
                             sourceOptions,
                             initialState
                         }) {

    const initial = {
        ...initialState
    };

    const reducer = (state, newState) => ({ ...state, ...newState });
    const [state, setState] = useReducer(reducer, initial);
    const {isPending, run: runSubmit} = useAsync({deferFn: submitForm});
    const {register, handleSubmit, setValue, triggerValidation, errors, watch} = useForm({
        mode: 'onBlur',
        defaultValues: {agreement: false},
    });

    let msgRequired = "Это поле обязательно для заполнения";
    register({name: 'patronymic', type: 'custom'});
    register({name: 'university', type: 'custom'}, {required: msgRequired});
    register({name: 'course', type: 'custom'}, {required: msgRequired});
    register({name: 'has_job', type: 'custom'}, {required: msgRequired});
    register({name: 'campaign', type: 'custom'}, {required: msgRequired});
    register({name: 'agreement', type: 'custom'}, {required: msgRequired});

    const watchFields = watch([
        'campaign',
        'has_job',
        'preferred_study_programs',
        'where_did_you_learn',
        'agreement'
    ]);
    const {
        campaign: selectedCampaignId,
        has_job: hasJob,
        preferred_study_programs: selectedStudyPrograms,
        where_did_you_learn: whereDidYouLearn,
        agreement: agreementConfirmed
    } = watchFields;
    let selectedCampaign = selectedCampaignId && campaigns.find(obj => {
        return obj.id === parseInt(selectedCampaignId);
    }).value;

    function handleInputChange(event) {
        const target = event.target;
        const value = target.type === 'checkbox' ? target.checked : target.value;
        const name = target.name;
        setValue(name, value);
        if (name === 'campaign') {
            setValue('preferred_study_programs', []);
        }
    }

    function handleSelectChange(option, name) {
        setValue(name, option);
        triggerValidation(name);
    }

    useEffect(() => {
        // Yandex.Passport global handlers (postMessage could be broken in IE11-)
        window.accessYandexLoginSuccess = (login) => {
            setState({isYandexPassportAccessAllowed: true});
            showNotification("Доступ успешно предоставлен", {type: "success"});
        };
        window.accessYandexLoginError = function(msg) {
            showNotification(msg, {type: "error"});
        };
    }, []);

    let handleAccessYandexLogin = (event) => {
        event.preventDefault();
        const {isYandexPassportAccessAllowed} = state;
        if (isYandexPassportAccessAllowed) {
            return false;
        }
        openAuthPopup(authBeginUrl, authCompleteUrl);
        return false;
    };

    function onSubmit(data) {
        let {has_job, course, university, ...payload} = data;
        payload['has_job'] = (has_job === "yes");
        payload['level_of_education'] = course && course.value;
        if (university) {
            if (university.__isNew__) {
                payload["university_other"] = university.value;
            } else {
                payload["university"] = university.value;
            }
        }
        runSubmit(endpoint, csrfToken, setState, payload);
    }

    const {
        isYandexPassportAccessAllowed,
        isFormSubmitted,
    } = state;
    let filteredStudyPrograms = studyProgramOptions.filter((program) => {
        if (selectedCampaign && selectedCampaign === "nsk") {
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
        <form className="ui form" onSubmit={handleSubmit(onSubmit)}>
            <fieldset>
                <h3>Личная информация</h3>
                <div className="row">
                    <InputField name="surname" label={"Фамилия"} inputRef={register({required: msgRequired})} wrapperClass="col-lg-4" errors={errors} />
                    <InputField name="first_name" label={"Имя"} inputRef={register({required: msgRequired})} wrapperClass="col-lg-4" errors={errors} />
                    <InputField name="patronymic" label={"Отчество"} onChange={handleInputChange} wrapperClass="col-lg-4" errors={errors} />
                    <InputField name="email" type="email" label={"Электронная почта"} inputRef={register({required: msgRequired})} wrapperClass="col-lg-4" errors={errors} />
                    <InputField name="phone" label={"Контактный телефон"} inputRef={register({required: msgRequired})} wrapperClass="col-lg-4" errors={errors}
                                placeholder="+7 (999) 1234567"/>
                </div>
            </fieldset>
            <fieldset>
                <h3>Аккаунты</h3>
                <div className="row">
                    <InputField name="stepic_id" label={"ID на stepik.org"}
                                wrapperClass="col-lg-4" errors={errors}
                                inputRef={register}
                                helpText={"https://stepik.org/users/xxxx, ID — это xxxx"}
                                placeholder="ХХХХ"/>
                    <InputField name="github_login" label={"Логин на github.com"}
                                wrapperClass="col-lg-4" errors={errors}
                                inputRef={register}
                                helpText={"https://github.com/xxxx, логин — это xxxx"}
                                placeholder="ХХХХ"/>
                    <div className="field col-lg-4 mb-2">
                        <label>Доступ к данным на Яндексе&nbsp;<YandexAccessTooltip/></label>
                        <div className="grouped inline">
                            <Checkbox
                                required
                                label={isYandexPassportAccessAllowed ? "Доступ разрешен" : "Разрешить доступ"}
                                disabled={isYandexPassportAccessAllowed}
                                checked={isYandexPassportAccessAllowed}
                                onChange={() => {}}
                                onClick={handleAccessYandexLogin}
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
                                components={{
                                    DropdownIndicator: null
                                }}
                                openMenuOnFocus={true}
                                isClearable={true}
                                onChange={handleSelectChange}
                                onBlur={e => triggerValidation("university")}
                                name="university"
                                placeholder=""
                                options={universities}
                                menuPortalTarget={document.body}
                                errors={errors}
                            />
                        </div>
                        <div className="help-text">
                            Расскажите, где вы учитесь или учились
                        </div>
                        <ErrorMessage errors={errors} name={"university"} />
                    </div>
                    <InputField name="faculty" label={"Специальность"}
                                wrapperClass="col-lg-4" errors={errors}
                                inputRef={register({required: msgRequired})}
                                helpText={"Факультет, специальность или кафедра"} />

                    <div className="field col-lg-4">
                        <div className="ui select">
                            <label htmlFor="">Курс</label>
                            <Select
                                onChange={handleSelectChange}
                                onBlur={e => triggerValidation("course")}
                                name="course"
                                isClearable={false}
                                placeholder="Выберите из списка"
                                options={educationLevelOptions}
                                menuPortalTarget={document.body}
                                required
                                errors={errors}
                            />
                            <ErrorMessage errors={errors} name={"course"} />
                        </div>
                    </div>
                </div>
                <div className="row">
                    <div className="field col-lg-12">
                        <label>Вы сейчас работаете?</label>
                        <RadioGroup required name="has_job" className="inline pt-0" onChange={handleInputChange}>
                            <RadioOption id="yes">Да</RadioOption>
                            <RadioOption id="no">Нет</RadioOption>
                        </RadioGroup>
                    </div>
                </div>
                {
                    hasJob && hasJob === "yes" &&
                        <div className="row ">
                            <div className="field col-lg-4">
                                <label htmlFor="position">Должность</label>
                                <Input name="position" id="position" ref={register} placeholder="" onChange={handleInputChange} />
                            </div>
                            <div className="field col-lg-4">
                                <label htmlFor="workplace">Место работы</label>
                                <Input name="workplace" id="workplace" ref={register} placeholder="" onChange={handleInputChange} />
                            </div>
                        </div>
                }
                <div className="row">
                    <MemoizedTextField name="experience"
                                       label="Расскажите об опыте программирования и исследований"
                                       wrapperClass="col-lg-8"
                                       inputRef={register}
                                       helpText="Напишите здесь о том, что вы делаете на работе, и о своей нынешней дипломной или курсовой работе. Здесь стоит рассказать о студенческих проектах, в которых вы участвовали, или о небольших личных проектах, которые вы делаете дома, для своего удовольствия. Если хотите, укажите ссылки, где можно посмотреть текст или код работ."
                                       errors={errors}/>
                    <MemoizedTextField name="online_education_experience"
                                       label="Вы проходили какие-нибудь онлайн-курсы? Какие? Какие удалось закончить?"
                                       wrapperClass="col-lg-8"
                                       inputRef={register}
                                       helpText="Приведите ссылки на курсы или их названия и платформы, где вы их проходили. Расскажите о возникших трудностях. Что понравилось, а что не понравилось в таком формате обучения?"
                                       errors={errors}/>
                </div>
            </fieldset>
            <fieldset>
                <h3>CS центр</h3>
                <div className="row">
                    <div className="field col-lg-12">
                        <label>Выберите отделение, в котором собираетесь учиться</label>
                        <RadioGroup required name="campaign" className="inline pt-0" onChange={handleInputChange}>
                            {campaigns.map((branch) =>
                                <RadioOption  key={branch.id} id={`campaign-${branch.value}`} value={branch.id}>
                                    {branch.label}
                                </RadioOption>
                            )}
                        </RadioGroup>
                    </div>
                </div>
                {
                    selectedCampaign && (selectedCampaign === "spb" || selectedCampaign === "nsk") &&
                    <Fragment>
                        <div className="row">
                            <div className="field col-lg-8">
                                <label>Какие направления  обучения из трех вам интересны в CS центре?</label>
                                <p className="text-small mb-2">
                                    Мы не просим поступающих сразу определиться с направлением обучения. Вам предстоит сделать этот выбор через год-полтора после поступления. Сейчас мы предлагаем указать одно или несколько направлений, которые кажутся вам интересными.
                                </p>
                                <div className="grouped">
                                    {filteredStudyPrograms.map((option) =>
                                        <Checkbox
                                            className={errors && errors.preferred_study_programs ? 'error' : ''}
                                            name="preferred_study_programs"
                                            key={option.value}
                                            ref={register({required: msgRequired})}
                                            value={option.value}
                                            label={option.label}
                                        />
                                    )}
                                </div>
                                <ErrorMessage errors={errors} name={"preferred_study_programs"} className="mt-2" />
                            </div>
                        </div>
                        {
                            selectedStudyPrograms && selectedStudyPrograms.includes('cs') &&
                            <div className="row">
                                <div className="field col-lg-8">
                                    <div className="ui input">
                                        <label htmlFor="preferred_study_programs_cs_note">Вы бы хотели заниматься исследованиями в области Computer Science? Какие темы вам особенно интересны?</label>
                                        <p className="text-small mb-2">
                                            Вы можете посмотреть список возможных тем и руководителей НИРов у нас на <a target="_blank" href="https://compscicenter.ru/projects/#research-curators" rel="noopener noreferrer">сайте</a>.
                                        </p>
                                        <textarea id="preferred_study_programs_cs_note" name="preferred_study_programs_cs_note" rows="6" ref={register} />
                                    </div>
                                </div>
                            </div>
                        }
                        {
                            selectedStudyPrograms && selectedStudyPrograms.includes('ds') &&
                            <div className="row">
                                <div className="field col-lg-8">
                                    <div className="ui input">
                                        <label htmlFor="preferred_study_programs_dm_note">Что вам больше всего интересно в области Data Science? Какие достижения последних лет вас особенно удивили?</label>
                                        <textarea id="preferred_study_programs_dm_note" name="preferred_study_programs_dm_note" rows="6" ref={register} />
                                    </div>
                                </div>
                            </div>
                        }
                        {
                            selectedStudyPrograms && selectedStudyPrograms.includes('se') &&
                            <div className="row">
                                <div className="field col-lg-8">
                                    <div className="ui input">
                                        <label htmlFor="preferred_study_programs_se_note">В разработке какого приложения, которым вы пользуетесь каждый день, вы хотели бы принять участие? Каких знаний вам для этого не хватает?</label>
                                        <textarea id="preferred_study_programs_se_note" name="preferred_study_programs_se_note" rows="6" ref={register} />
                                    </div>
                                </div>
                            </div>
                        }
                    </Fragment>
                }
                {
                    selectedCampaign && selectedCampaign === "distance" &&
                    <div className="row">
                        <div className="field col-lg-5">
                            <Input required name="living_place" id="living_place" placeholder="В каком городе вы живёте?" ref={register({required: msgRequired})} />
                        </div>
                    </div>
                }

                <div className="row">
                    <MemoizedTextField name="motivation"
                                       label="Почему вы хотите учиться в CS центре? Что вы ожидаете от обучения?"
                                       wrapperClass="col-lg-8"
                                       inputRef={register({required: msgRequired})}
                                       errors={errors}/>
                    <MemoizedTextField name="probability"
                                       label="Что нужно для выпуска из CS центра? Оцените вероятность, что вы сможете это сделать"
                                       wrapperClass="col-lg-8"
                                       inputRef={register({required: msgRequired})}
                                       errors={errors}/>
                    <MemoizedTextField name="additional_info"
                                       label="Напишите любую дополнительную информацию о себе"
                                       wrapperClass="col-lg-8"
                                       inputRef={register}
                                       errors={errors}/>
                </div>
                <div className="row">
                    <div className="field col-lg-8">
                        <label className="mb-4">Откуда вы узнали о CS центре?</label>
                        <div className="grouped">
                            {sourceOptions.map((option) =>
                                <Checkbox
                                    key={option.value}
                                    ref={register({required: msgRequired})}
                                    className={errors && errors.where_did_you_learn ? 'error' : ''}
                                    name="where_did_you_learn"
                                    value={option.value}
                                    label={option.label}
                                />
                            )}
                        </div>
                        <ErrorMessage errors={errors} name={"where_did_you_learn"} className="mt-2" />
                    </div>
                    {
                        whereDidYouLearn && whereDidYouLearn.includes("other") &&
                        <InputField name="where_did_you_learn_other"
                                    wrapperClass="animation col-lg-5"
                                    inputRef={register({required: msgRequired})}
                                    placeholder="Ваш вариант"
                                    errors={errors} />
                    }
                </div>
            </fieldset>
            <div className="row">
                <div className="col-lg-12">
                    <div className="grouped mb-4">
                        <Checkbox
                            required
                            name={"agreement"}
                            label={<Fragment>Настоящим подтверждаю свое согласие на обработку Оператором моих персональных данных в соответствии с <a target="_blank" href="https://compscicenter.ru/policy/" rel="noopener noreferrer">Политикой в отношении обработки персональных данных Пользователей Веб-сайта</a>, а также гарантирую достоверность представленных мной данных</Fragment>}
                            onChange={handleInputChange}
                        />
                    </div>
                    <button type="submit" disabled={!agreementConfirmed || isPending} className="btn _primary _m-wide">Подать заявку</button>
                </div>
            </div>
        </form>
    );
}

ApplicationForm.propTypes = {
    initialState: PropTypes.shape({
        isYandexPassportAccessAllowed: PropTypes.bool.isRequired,
    }).isRequired,
    endpoint: PropTypes.string.isRequired,
    csrfToken: PropTypes.string.isRequired,
    authBeginUrl: PropTypes.string.isRequired,
    authCompleteUrl: PropTypes.string.isRequired,
    campaigns: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired,
        id: PropTypes.number.isRequired,
    })).isRequired,
    sourceOptions: PropTypes.arrayOf(optionStrType).isRequired,
    universities: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.number.isRequired,
        label: PropTypes.string.isRequired,
        branch_id: PropTypes.number.isRequired
    })).isRequired,
    educationLevelOptions: PropTypes.arrayOf(optionStrType).isRequired,
    studyProgramOptions: PropTypes.arrayOf(optionStrType).isRequired
};

export default ApplicationForm;
