# Frappe Learning → OVER U: технический аудит

Аудит исходников от 8 октября 2026 года. База локальной ветки `over-u/development`: официальный `frappe/lms`, релиз `v2.64.0`, commit `7c46bb8f4976222b3f6aa84368551c424edaa194`. Сравнение с develop `c65904a362c4d4951de8dc44080464aa7eb0e276` проведено отдельно: его архитектура и требования отличаются. Результаты запуска и проверки см. в `VALIDATION.md`.

## Архитектура и зависимости

Это Frappe-приложение, а не независимый Vue-сайт. Python-контроллеры DocType и JSON-метаданные задают модели, валидацию и разрешения; MariaDB хранит документы и дочерние таблицы. Redis используется для кэша, очередей и realtime. Bench запускает HTTP-сервер, socket.io, scheduler и workers. Vue 3 / Vue Router / Pinia / frappe-ui / Vite обслуживают SPA по `/lms`; Frappe Desk остаётся отдельным административным интерфейсом.

Сборка frontend записывает ассеты в `lms/public/frontend` и Jinja entry в `lms/www/_lms.html`. `lms/www/_lms.py` передаёт язык, имя site, CSRF и путь LMS. Состояние входа и роли запрашиваются с сервера; нельзя переносить роль/права в один только frontend.

Связи: **LMS Course → Chapter Reference → Course Chapter → Lesson Reference → Course Lesson**. Пользователи — стандартные Frappe User. Course Instructor связывает преподавателя с курсом. LMS Enrollment связывает ученика с курсом; LMS Course Progress хранит завершение конкретного урока. Процент и current_lesson в Enrollment — производные данные/указатель, а не источник разрешений.

Выбранная совместимая комбинация: LMS 2.64.0, Frappe 16.51.0 (`6b450a166e076dd842e4db7ea0843f62881e62ac`), payments version-16 (`cca07d9f9392e2ea0e521c5975151db9e4b6c321`), Python 3.14, Node 24, MariaDB 10.8 и Redis 7. Последний develop LMS требует Frappe 17. Слепой `bench get-app payments` скачивает develop и нарушает эту совместимость.

## Карта реализации

Пути ниже относительно корня репозитория. API доступны как `/api/method/<полное имя>`. Стандартные `frappe.client.*` дополнительно проверяют DocPerm и permission hooks.

| Функция | Vue страницы / компоненты | API / Python | Модели |
|---|---|---|---|
| Каталог и интерфейс ученика | `frontend/src/pages/Home/Home.vue`, `pages/Courses/Courses.vue`, `pages/Courses/CourseDetail.vue`, `pages/Courses/CourseOverview.vue`, `pages/Courses/StudentCourseProgress.vue`, `components/CourseCard.vue` | `lms.lms.api.get_user_info`, `lms.lms.utils.get_course_outline`, `frappe.client.get_list/get` | User, LMS Course, LMS Enrollment |
| Интерфейс преподавателя / аналитика | `pages/Courses/CourseDashboard.vue`, `pages/AssignmentSubmissionList.vue`, `pages/QuizSubmissions.vue`, `components/CourseOutline.vue` | `lms/lms/api.py`: статистика, enrollments; стандартные list/document resources | Course Instructor, LMS Enrollment, LMS Course Progress, submissions |
| Редактор курса и модулей | `pages/Courses/CourseEditor.vue`, `pages/Courses/CourseForm.vue`, `pages/Courses/CoursePublishSettings.vue`, `pages/Forms/ChapterForm.vue`, `components/CourseOutline.vue`, `components/ChapterRow.vue` | `lms.lms.api.create_lesson`, `update_lesson_index`, `update_chapter_index`; `frappe.client.insert/set_value` | LMS Course, Course Chapter, Chapter Reference, Lesson Reference |
| Редактор урока | `pages/LessonForm.vue`, EditorJS plugins в `components/` | `lms.lms.utils.get_lesson_creation_details`; `lms/lms/doctype/course_lesson/course_lesson.py`: sanitize, backreferences | Course Lesson: content (EditorJS JSON), body (legacy Markdown), instructor_content |
| Прохождение урока | `pages/Lesson.vue`, `components/StudentLessonSidebar.vue`, `components/LockedLessonNotice.vue`, `components/LessonContent.vue`, `components/VideoBlock.vue` | `lms.lms.utils.get_lesson`, `get_course_outline`; `lms.lms.permissions.get_locked_lessons/get_lesson_gate` | Course Lesson, LMS Course Progress, LMS Video Watch Duration |
| Прогресс и последовательность | `pages/Lesson.vue`, `utils/lessonProgress.ts`, `components/StudentLessonSidebar.vue` | `lms.lms.doctype.course_lesson.course_lesson.save_progress`, `get_quiz_progress`, `get_assignment_progress`; `lms.lms.api.mark_lesson_progress`; `lms.lms.utils.compute_locked_lessons/recalculate_course_progress` | LMS Course.enforce_lesson_completion, LMS Settings.enforce_quiz_completion/enforce_assignment_completion, LMS Enrollment, LMS Course Progress |
| Тест и редактирование | `pages/QuizPage.vue`, `pages/Forms/QuizForm.vue`, `components/Quiz.vue`, `components/QuizBlock.vue`, `components/Quiz/QuestionEditor.vue`, `pages/QuizSubmission.vue` | `lms.lms.utils.get_quiz_with_questions`, `lms.lms.doctype.lms_quiz.lms_quiz.submit_quiz/check_answer`; `process_results`, `save_progress_after_quiz` | LMS Quiz, LMS Question, LMS Quiz Question, LMS Quiz Submission, LMS Quiz Result |
| Отправка / проверка домашней работы | `components/Assignment.vue`, `pages/AssignmentSubmission.vue`, `pages/AssignmentSubmissionList.vue`, `pages/Forms/AssignmentForm.vue` | `lms.lms.utils.get_assignment`, `lms.lms.api.get_own_assignment_submission`; `frappe.client.insert/set_value`; `lms/lms/doctype/lms_assignment_submission/lms_assignment_submission.py` | LMS Assignment, LMS Content Author, LMS Assignment Submission, File, Notification Log |
| Сессия, роли и доступ | `frontend/src/stores/user*`, `stores/session*`, `router.js`, `routes.js` | `lms/hooks.py`, `lms/lms/permissions.py`, Frappe DocPerm и CSRF | User, Role, DocPerm, Course Instructor |

Контроллер и метаданные каждой модели лежат в `lms/lms/doctype/<snake_case_name>/<snake_case_name>.py/.json`. Карта относится к выбранному релизу: develop уже содержит отдельный индекс `LMS Lesson Assessment` и более детальные permissions для assessments/submissions; эти различия нельзя переносить на релиз как уже установленные возможности.

## Assignment: что работает штатно и что изменено

Штатно поддерживаются Text, URL, Image, PDF и Document. У одной пары assignment/member одна submission; повторная попытка редактирует тот же документ. Статусы: Not Graded, Pass, Fail, Not Applicable. Преподаватель задаёт evaluator/comments/status; сохраняются изменения и уведомление ученику. `grade_assignment` управляет нужным режимом проверки в интерфейсе, но не делает Pass условием завершения урока.

В `get_assignment_progress()` штатное условие — **существует submission**, независимо от статуса. Поэтому `enforce_assignment_completion` означает «отправлено», а не «зачтено». Установить только этот флаг недостаточно.

Реализован минимальный seam в core: `lms_assignment_completion_filters`. В исходном цикле проверки Assignment добавлено получение дополнительных фильтров из hooks. Без приложения OVER U штатное поведение сохраняется. Это единственный функциональный diff в LMS core; заменять глобальную функцию monkey patch или копировать весь `save_progress()` не требуется.

Отдельное Frappe-приложение в `over-u/apps/over_u` содержит:

- custom field `LMS Course.over_u_require_assignment_pass`, по умолчанию выключенный;
- `completion_filters()` добавляет `status=Pass` только для выбранных курсов;
- `validate_submission()` проверяет преподавателя именно этого курса, запрещает зачёт себе, фиксирует evaluator, запрещает замену зачтённого ответа и перенос submission на другого ученика/assignment; исправление после Fail возвращает Not Graded;
- `update_assignment_progress()` после Pass пересчитывает прогресс **от имени ученика**, сохраняя контекст преподавателя; проверяет блокировку и все assessments урока. Изменение происходит в той же транзакции, без commit внутри document hooks;
- при отмене Pass удаляется только completion этого assignment-урока, если его требования больше не выполнены. Завершённые позже уроки не стираются: это штатная политика сохранения уже выполненной работы, а не строгий откат всей цепочки;
- `validate_progress()` дополнительно проверяет enrollment, последовательность, курс урока, тест и Pass при записи LMS Course Progress;
- override whitelisted `save_progress` проверяет соответствие переданного course реальному курсу lesson для opt-in курсов и делегирует штатному обработчику. Это защищает также ветку, возвращающую уже существующий progress, где document validate не запускается;
- idempotent seed и интеграционные проверки.

Особенность релиза: SPA не передаёт submission.lesson при отправке задания. Обработчик находит урок по реальному EditorJS/Markdown содержимому курса, а не доверяет этому полю в payload ученика. На большом количестве уроков такой поиск стоит заменить индексом размещений; develop уже предлагает основу такого индекса. Для демо один assignment размещён ровно в одном уроке.

## Можно ли заменить весь интерфейс ученика

**Да, архитектурно это возможно с сохранением backend. Риск умеренный при изоляции frontend и контрактных тестах; считать произвольный UI drop-in заменой небезопасно.**

Рекомендуется отдельное Frappe-приложение `over_u` с собственным SPA на `/school` и тем же origin/site. Штатные `/lms` для преподавателя и `/desk` для администратора остаются доступны. Новый UI использует серверные course/outline/lesson endpoints, серверный submit_quiz, Assignment Submission и save_progress. Курс, контент, оценки и enrollment продолжают храниться в существующих DocType.

Это сохраняет cookie-сессию, CSRF, загрузку файлов, приватные URL, переводы и права без отдельного auth-сервиса. При отдельном домене потребуется специальное решение для cookies, CORS/CSRF и токенов; административные API keys нельзя встраивать в браузер.

Необходимо сохранить: обработку locked/not_found и resume, realtime update_lesson_progress, состояния «отправлено/ожидает проверки/Fail/Pass», повторные попытки теста, проценты и минимальный балл, lesson ordering и структуру EditorJS. Ответы теста оценивает сервер; frontend не отправляет доверенные marks или percentage. Новые endpoints-адаптеры следует добавлять в `over_u`, не дублируя проверку LMS прав собственными упрощёнными условиями.

Риски обновления: whitelisted Python endpoints и DocType не обещают стабильный внешний API; payload и frontend imports меняются между версиями. В частности develop переходит на Frappe 17 и новый индекс assessment placements. Нужны pinned releases, тесты контрактов и отдельный staging прогон upgrade. Хранить fork-diff маленьким и периодически предлагать upstream универсальную точку расширения.

## Ограничения и следующий этап

1. Последовательность штатно охватывает все уроки. Отдельного понятия «необязательный урок, не участвующий в цепочке» эта настройка не даёт. В демо обязательны все шесть; optional/branching проектировать отдельно.
2. Проходной балл и quiz scoring доступны штатно. Лимит попыток способен навсегда заблокировать следующие уроки; в демо попытки не ограничены. Для школы нужен сценарий восстановления доступа преподавателем.
3. Dwell time текста и окончание видео — frontend события. Это не подтверждение усвоения знаний и не защищённая серверная аттестация просмотра; API завершения проверяет assessments, а не полную историю просмотра. Для обязательного просмотра нужен отдельно сформулированный критерий, серверный учёт и понятный обход технических сбоев.
4. Авторизация в стабильном релизе не равна более новым изменениям develop. До публичной школы необходимо проверить ограничения доступа преподавателей к чужим submissions, приватность вложений, generic REST, instructor_content, quiz answers, привязку progress к course. В metadata Assignment Submission релиза включён `make_attachments_public`; нельзя считать домашние файлы приватными без проверки. Текстовое демо не решает privacy загрузок.
5. Отмена Pass блокирует ещё не выполненные последующие уроки, но не отзывает уже завершённые и сертификаты автоматически. Требуется бизнес-правило для таких случаев и журнал оценок/версий домашней работы, если школа требует неизменяемую историю попыток.
6. Учебные материалы, email-доставка, платежи, видеохостинг, домен, backups и production hardening в демо не настраиваются. Compact Docker stack — development, без production SLA; stop/start сохраняет DB/bench volumes. Маршрутизация и публичный доступ требуют отдельного deployment.
7. LMS распространяется под AGPL-3.0-or-later. Сохранить лицензию/атрибуцию и спланировать предоставление исходников модификаций пользователям сетевого сервиса согласно лицензии.
8. Уникальность assignment/member и последовательные изменения оценок проверяются приложением. Параллельные submissions, grading/resubmission и транзакционные гонки не покрыты нагрузочной проверкой; до production нужны отдельные сценарии конкурентной записи.

Следующий этап: закончить remote fork и CI; согласовать правила required/optional, retry и отмены зачёта; закрыть подтверждённые security/privacy gaps выбранной версии; затем прототипировать собственный student SPA на `/school` с небольшим API-адаптером. Сначала один сквозной путь «каталог → курс → урок → тест → домашнее задание → Pass → следующий урок», затем остальные student-facing возможности. Полный redesign и переработка LMS backend в текущем этапе не выполняются.
