# OVER U: первый технический этап

Upstream: <https://github.com/frappe/lms>. Локальная ветка: `over-u/development`, база — `v2.64.0`. Исходные возможности LMS сохранены; redesign не выполнен. Технический аудит и карта реализации: [ARCHITECTURE.md](docs/ARCHITECTURE.md). Фактически проверенные результаты: [VALIDATION.md](docs/VALIDATION.md).

## Запуск development

Нужны Docker Compose, Git и x86_64 Linux runtime. Контейнер содержит Python 3.14, Node 24 и Bench; установка на хост не нужна. MariaDB/Redis не публикуют порты. HTTP/socket.io привязаны к 127.0.0.1. Код монтируется из этого checkout; DB и Bench живут в named volumes.

Создайте отдельный файл окружения вне Git, например `over-u-runtime/dev.env`, с переменными `OVER_U_DB_PASSWORD`, `OVER_U_ADMIN_PASSWORD` и `OVER_U_DEMO_PASSWORD`. Используйте случайные пароли. В managed cloud при необходимости задайте `OVER_U_CA_BUNDLE` на системный объединённый CA bundle; он передаётся при сборке как secret и в runtime read-only, не копируется в image.

Из корня репозитория:

```sh
docker compose --env-file /absolute/path/dev.env -f over-u/dev/compose.yml up -d --build
docker compose --env-file /absolute/path/dev.env -f over-u/dev/compose.yml logs -f frappe
```

В этой managed-среде buildx требует writable config directory: добавьте к команде `BUILDX_CONFIG=/workspace/over-u-runtime/buildx`. Это не меняет Docker registry credentials. Обычному локальному Docker эта настройка не нужна.

Адрес: <http://over-u.localhost:8000/lms>. Для браузеров, не разрешающих `.localhost`, сопоставьте `over-u.localhost` с 127.0.0.1. Cloud-hosted loopback URL доступен внутри среды; для доступа с рабочего компьютера потребуется её штатный preview/port forwarding либо локальный запуск.

Учётные записи: `Administrator` (OVER_U_ADMIN_PASSWORD), `teacher@over-u.example.com`, `student1@over-u.example.com`, `student2@over-u.example.com` (OVER_U_DEMO_PASSWORD). Преподаватель имеет Course Creator и назначен instructor курса; ученики имеют LMS Student и Enrollment. Пароли не входят в repository/evidence.

Seed создаёт отдельный курс «OVER U — Основы осознанного обучения», 3 модуля / 6 уроков, штатное локальное демонстрационное видео, тест из 4 вопросов с порогом 75%, текстовое задание с ручным Pass/Fail. Повторный запуск seed не стирает работы или прогресс. Остановка `docker compose ... stop` сохраняет данные; для возобновления `up -d`. `down --volumes` удалит данные — не используйте для обычного перезапуска.

## Разработка и проверки

```sh
docker compose --env-file /absolute/path/dev.env -f over-u/dev/compose.yml exec -u frappe frappe bash
cd /home/frappe/frappe-bench
bench --site over-u.localhost run-tests --app over_u --module over_u.test_policy
bench --site over-u.localhost execute over_u.school.manifest
bench build --app lms
bench --site over-u.localhost clear-cache
```

Frappe проверяет backend изменения через document events; frontend пересобирается командой выше. Интеграционные тесты используют отдельного тестового ученика и транзакционный откат. Не запускайте tests на production.

Единственное изменение функционального LMS core — `lms_assignment_completion_filters` в `get_assignment_progress()`. Вся OVER U политика, custom field, demo seed и tests находятся в отдельном приложении `over-u/apps/over_u`. При удалении extension hook штатная проверка снова означает «задание отправлено».

## GitHub fork

Удалённый fork пока не создан: connector имеет read-доступ, отдельного fork tool нет; GitHub CLI из managed environment получает Forbidden на `api.github.com`. Локальный remote `upstream` указывает на официальный repository. После настройки GitHub доступа:

```sh
gh repo fork frappe/lms --fork-name over-u-learning --clone=false
git remote add origin https://github.com/YOUR_OWNER/over-u-learning.git
git push -u origin over-u/development
```

Перед этой операцией выберите владельца fork и проверьте, что origin — действительно fork `frappe/lms`. Публикация текущего локального кода ещё не выполнена.

## Демонстрация и evidence

[Отчёт о проверках](docs/VALIDATION.md), [экраны](docs/SCREENS.md), [HTML-галерея](evidence/index.html). Все изображения сняты с работающего stock UI.

Браузерный сценарий требует Playwright (devDependencies проекта), Chromium на хосте и файл окружения. Запускайте на свежем demo-состоянии: `OVER_U_ENV_FILE=/absolute/path/dev.env OVER_U_CHROMIUM=/path/to/chromium node over-u/dev/browser-evidence.mjs`. Он изменяет работы и progress ученика 1; не является повторяемым без подготовки состояния. Backend tests откатывают собственные транзакции. Для read-only сводки: `bench --site over-u.localhost execute over_u.school.runtime_summary`.
