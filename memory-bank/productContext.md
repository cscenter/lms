# Product Context

This file provides a high-level overview of the project and the expected product that will be created. Initially it is based upon projectBrief.md (if provided) and all other available project-related information in the working directory. This file is intended to be updated as the project evolves, and should be used to inform all other modes of the project's goals and context.
2025-03-31 16:14:09 - Log of updates made will be appended as footnotes to the end of this file.

*

## Project Goal

Система управления обучением (LMS - Learning Management System) для образовательных учреждений, связанных с компьютерными науками и анализом данных, включая Computer Science Center, Computer Science Club и Школу анализа данных Яндекса. Система предназначена для полного цикла образовательного процесса: от приема студентов до выдачи сертификатов об окончании обучения.

## Key Features

* **Управление приемной кампанией**
  - Регистрация и обработка заявок абитуриентов
  - Проведение вступительных тестов, олимпиад и интервью
  - Управление расписанием собеседований
  - Оценка и отбор кандидатов
  - Хранение и анализ результатов олимпиад

* **Управление курсами и учебными материалами**
  - Создание и редактирование курсов
  - Управление учебными материалами (лекции, презентации, видео)
  - Расписание занятий
  - Управление преподавателями и их ролями

* **Система заданий и оценивания**
  - Создание и проверка заданий
  - Автоматическая и ручная проверка решений
  - Система оценивания и обратной связи
  - Интеграция с системами проверки кода (Yandex.Contest, Gerrit)

* **Проектная работа**
  - Управление проектами студентов
  - Назначение руководителей проектов
  - Отслеживание прогресса и оценка результатов

* **Уведомления и коммуникация**
  - Система уведомлений (email, веб)
  - Обратная связь между студентами и преподавателями

* **Интеграция с внешними сервисами**
  - Yandex.Contest (для проверки заданий и проведения олимпиад)
  - Gerrit (для код-ревью)
  - Yandex.Disk (для хранения файлов)
  - Yandex.Passport и LDAP (для аутентификации)

## Overall Architecture

Проект представляет собой многосайтовое Django-приложение с общим кодом и специфичными компонентами для каждого образовательного учреждения:

* **Сайты/поддомены:**
  - compscicenter_ru - Computer Science Center
  - compsciclub_ru - Computer Science Club
  - lk_yandexdataschool_ru - Личный кабинет Школы анализа данных Яндекса
  - lms - общий код и компоненты для всех сайтов

* **Основные компоненты:**
  - **apps/admission** - управление приемной кампанией, включая проведение олимпиад ШАД
  - **apps/courses** - управление курсами и учебными материалами
  - **apps/learning** - управление учебным процессом
  - **apps/tasks** - система заданий
  - **apps/grading** - система оценивания
  - **apps/projects** - управление проектами
  - **apps/users** - управление пользователями и их ролями
  - **apps/notifications** - система уведомлений
  - **apps/api** - REST API для взаимодействия с фронтендом и внешними сервисами
  - **apps/auth** - аутентификация и авторизация
  - **apps/code_reviews** - система код-ревью
  - **apps/stats** - сбор и анализ статистики

* **Технологический стек:**
  - Backend: Python 3.x, Django 2.2.x, PostgreSQL 11, Redis, Celery
  - API: Django REST Framework
  - Frontend: Jinja2, Webpack
  - Инфраструктура: Docker, Kubernetes