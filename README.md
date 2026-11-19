# Фудграм

Сервис рецептов: публикация блюд, подписки на авторов, избранное и список
покупок. При скачивании списка количества одинаковых ингредиентов суммируются
с сохранением единиц измерения.

Бэкенд: Python 3.14, Django 5.2 LTS, Django REST Framework, Djoser.
Инфраструктура: PostgreSQL 17, Gunicorn, nginx, Docker Compose, GitHub Actions.
React-интерфейс и OpenAPI-спецификация предоставлены Яндекс Практикумом.

## Локальный запуск

Требуются запущенный Docker Desktop с Linux-контейнерами и Docker Compose
2.20 или новее. Python 3.14 нужен для генерации настроек; далее проект работает
в контейнерах.

```bash
git clone https://github.com/LandLordME/foodgram.git
cd foodgram
python scripts/bootstrap_env.py --demo
docker compose up -d --build --wait
```



| Страница | Адрес по умолчанию |
| --- | --- |
| Сайт | http://localhost:8080/ |
| API | http://localhost:8080/api/ |
| Документация | http://localhost:8080/api/docs/ |
| Django admin | http://localhost:8080/admin/ |

Порт меняется через `PUBLIC_PORT` в `.env`. Бэкенд автоматически выполняет
миграции, сбор статики и импорт ингредиентов. Контейнер frontend копирует
интерфейс в том и завершает работу. Постоянно работают три контейнера:
PostgreSQL, backend и nginx.

При `SEED_DEMO=True` создаются `chef_anna@example.com`, `chef_ivan@example.com`
и `demo_admin@example.com` с паролем из `DEMO_PASSWORD`. Последний аккаунт —
суперпользователь. Для каждого создаётся рецепт. Повторная загрузка не
дублирует данные и не меняет существующие пароли. Публичного пароля по
умолчанию нет. Для отдельного администратора:

```bash
docker compose exec backend python manage.py createsuperuser
```

Из папки `infra` также работает `docker compose up -d --build --wait`:
файл курса подключает основной `compose.yaml`.

## Возможности и модели

- Пользователи с уникальными email/username, именем, фамилией и аватаром.
- Рецепты с автором, изображением, описанием, временем приготовления и тегами.
- Ингредиенты с единицами измерения; количество хранится в связующей модели.
- Подписки, избранное и покупки с ограничениями уникальности в БД.
- Регистрация, токены, смена пароля, загрузка и удаление аватара.
- Поиск по началу названия ингредиента без учёта регистра, включая кириллицу.
- Пагинация по шесть рецептов, параметр `limit`, сортировка от новых к старым.
- Фильтры `author`, `tags`, `is_favorited`, `is_in_shopping_cart`.
- Подписки с параметром `recipes_limit` и общим `recipes_count`.
- Постоянные короткие ссылки `/s/<code>` с переходом на страницу рецепта.

Все модели доступны в Django admin. Настроены поиск пользователей по имени и
email, рецептов по названию/автору и ингредиентов по названию. У рецепта
отображается счётчик добавлений в избранное. Через API рецепты редактируют
авторы и администраторы; личные списки доступны только владельцам.
Контракт API находится в `docs/openapi-schema.yml`.

## Данные

```bash
docker compose exec backend python manage.py import_ingredients
docker compose exec backend python manage.py import_ingredients /data/ingredients.csv
```

Импорт JSON/CSV идемпотентен. Исходный набор содержит 2186 уникальных
ингредиентов; создаются теги «Завтрак», «Обед» и «Ужин».
PostgreSQL, медиа, статика и интерфейс сохраняются в именованных томах.
`docker compose down` сохраняет тома; ключ `-v` удаляет их вместе с данными.

Перед обновлением сервера сохраните резервную копию базы:

```bash
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > foodgram-backup.sql
```

## Разработка и тесты без Docker

Из корня проекта в PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
$env:DEBUG = 'True'
$env:DB_ENGINE = 'sqlite'
python backend/manage.py migrate
python backend/manage.py import_ingredients
python backend/manage.py runserver
```

SQLite применяется при локальной разработке; обычный запуск использует
PostgreSQL. Модели и миграции одинаковы для обеих баз.

```bash
python -m flake8 backend
python backend/manage.py makemigrations --check --dry-run
python backend/manage.py test tests
```

Семь сценарных тестов проверяют права, изоляцию пользователей, суммы покупок
с разными единицами, неизменность рецепта после невалидного запроса, короткие
ссылки, кириллический поиск, подписки и жизненный цикл аватара/токена.

### Postman

Исходная коллекция курса сохранена без изменений. Одна проверка поиска в ней
использует регистрозависимый JavaScript `startsWith`, хотя задание требует
регистронезависимый поиск. На ингредиентах «Буррата» и «багет» получается ложный
сбой. Скрипт создаёт отдельную копию и исправляет только это сравнение:

```bash
python scripts/prepare_postman.py
npm install --global newman@6.2.3
newman run verification-output/foodgram.postman_collection.json --env-var baseUrl=http://127.0.0.1:8000
```

Коллекция создаёт тестовые аккаунты и рецепты: запускайте её на отдельной
локальной базе. В CI используется новая PostgreSQL-база. Для повторного
локального запуска можно задать новый SQLite-файл через `SQLITE_PATH`.

## Публикация и CI/CD

Опубликованные образы:

- [landlordme/foodgram-backend](https://hub.docker.com/r/landlordme/foodgram-backend)
- [landlordme/foodgram-frontend](https://hub.docker.com/r/landlordme/foodgram-frontend)
- [landlordme/foodgram-nginx](https://hub.docker.com/r/landlordme/foodgram-nginx)

Доступны теги `latest` и SHA проверенных коммитов.
Для запуска этих образов укажите `DOCKERHUB_USERNAME=landlordme` в `.env`.

В репозитории `LandLordME/foodgram` настроены `DOCKERHUB_USERNAME=landlordme`
и секрет `DOCKERHUB_TOKEN`. [Проверка автоматической публикации](https://github.com/LandLordME/foodgram/actions/runs/44174462254)
успешно выполнила тесты и отправила все три образа. Токен `foodgram-ci` имеет
права Read/Write и действует до 17 декабря 2026 года. Для продолжения публикации
после этой даты обновите токен Docker Hub и значение секрета в GitHub.

Workflow `.github/workflows/foodgram.yml` выполняет PEP 8, проверки Django и
миграций, тесты на PostgreSQL, 157 запросов Postman, сборку интерфейса и
проверку Docker-стека, документации и статики. Затем публикует три образа в
Docker Hub с тегами `latest` и SHA коммита и при включённом деплое обновляет
сервер через SSH.

В GitHub Settings → Secrets and variables → Actions задаются:

| Тип | Название | Назначение |
| --- | --- | --- |
| Variable | `DOCKERHUB_USERNAME` | Пользователь Docker Hub; включает публикацию |
| Secret | `DOCKERHUB_TOKEN` | Токен Docker Hub для публикации образов |
| Variable | `DEPLOY_ENABLED` | `true` включает деплой |
| Secret | `SSH_HOST` | Адрес сервера |
| Secret | `SSH_USER` | Пользователь сервера |
| Secret | `SSH_PORT` | Порт SSH; по умолчанию 22 |
| Secret | `SSH_KEY` | Закрытый ключ для деплоя |
| Secret | `SSH_KNOWN_HOSTS` | Проверенный публичный ключ SSH-сервера |

В новом репозитории до настройки Docker Hub workflow выполняет проверки,
пропуская публикацию и деплой. Для деплоя используется GitHub Environment
`production`.

На сервере должны быть Docker Engine и Compose. В `~/foodgram/.env` задаются
отдельные production-секреты, `DOCKERHUB_USERNAME`, домен/IP в `ALLOWED_HOSTS`
(с сохранением `localhost,127.0.0.1` для проверки здоровья) и `PUBLIC_PORT`.
Настройки: `DEBUG=False`, `SEED_DEMO=False`. Для публичного сервиса настройте
HTTPS, затем `HTTPS_ENABLED=True` и HTTPS-адрес в `CSRF_TRUSTED_ORIGINS`.
Адрес и домен сервера зависят от выбранного пользователем хостинга.

Ручной запуск опубликованных образов:

```bash
docker compose -f compose.production.yaml pull
docker compose -f compose.production.yaml up -d --wait
```

Workflow копирует production-compose как `~/foodgram/compose.yaml` и обновляет
контейнеры образами SHA проверенного коммита. `.env` остаётся на сервере и не
передаётся в GitHub.

## Состав репозитория

`backend/` — Django, API, миграции и тесты; `frontend/` — React SPA;
`infra/` — nginx; `data/` — ингредиенты; `docs/` — OpenAPI и ReDoc;
`scripts/` — подготовка окружения и проверок; `compose.yaml` — локальная
сборка; `compose.production.yaml` — запуск из Docker Hub.

