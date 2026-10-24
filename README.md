# Хранилище данных магазина изделий ручной работы

Лабораторная по «Аналитике больших данных»: витрина по заказчикам (Go + PostgreSQL),
загрузка CSV из внешнего источника в схему `external_source` (Airflow), журнал изменений и синхронизация с MongoDB.

## Стек

| Сервис | Порт | Зачем |
|---|---|---|
| PostgreSQL | `5435` | хранилище: схема `public` (задание 1), `external_source` (задание 2), таблица `logs` (задание 3) |
| MongoDB | `27017` | коллекции `clients`, `masters`, `orders`, `logs` |
| mongo-express | `8082` | веб-UI MongoDB - посмотреть/поправить коллекции (логин/пароль в `.env`, по умолчанию `admin`/`admin`) |
| Apache Airflow (standalone) | `8080` | DAG-и `load_external_source` и `sync_mongo` |

```
handmade_market/
├── dags/                    # load_external_source (CSV -> external_source), sync_mongo (PG -> Mongo)
├── migrations/              # SQL-миграции (up/down), применяются при первом старте
├── data/csv/                # исходные CSV-файлы
├── scripts/migrate.sh       # скрипт миграций
├── repo.go, repo_test.go    # SQL витрины + интеграционный тест
└── repo_mock_test.go        # unit-тест витрины (pgxmock)
```

CI: `.github/workflows/ci.yml` - на каждый push: `go vet` + `go test` (Postgres как service-контейнер) и `py_compile` DAG-ов.

## Запуск

```bash
cd handmade_market

cp .env.example .env        # .env в git не попадает

python -m venv venv

pip install -r requirements.txt

docker compose up -d

# Airflow UI
http://localhost:8080       # admin / пароль см. ниже

# веб-UI MongoDB
http://localhost:8082       # admin / admin (см. .env)
```

Пароль Airflow:

```bash
docker exec handmade-market-airflow cat /opt/airflow/standalone_admin_password.txt
```

## Команды

```bash
# миграции
./scripts/migrate.sh up
./scripts/migrate.sh down

# разовый прогон DAG-ов
docker exec handmade-market-airflow airflow dags test load_external_source   # CSV -> external_source
docker exec handmade-market-airflow airflow dags test sync_mongo             # PG -> MongoDB

# тесты (контейнер с Go, т.к. локально нужен toolchain 1.27.1)
MSYS_NO_PATHCONV=1 docker run --rm --network handmade_market_default \
  -e TEST_DATABASE_DSN="postgres://postgres:postgres@db:5432/handmade_market?sslmode=disable" \
  -v "$(pwd):/app" -w //app \
  golang:1.27.1-alpine go test -v ./...
# после тестов: ./scripts/migrate.sh up

# консоли
docker exec -it handmade-market-pg psql -U postgres -d handmade_market
docker exec -it handmade-market-mongo mongosh handmade_market

# остановить / остановить и стереть данные
docker compose down
docker compose down -v
```

## Переменные окружения (.env)

Креды и порты в `handmade_market/.env` (шаблон - `.env.example`):
`POSTGRES_USER/PASSWORD/DB/PORT`, `MONGO_PORT`, `MONGO_EXPRESS_PORT/USER/PASSWORD`,
а также `PG_DSN`, `MONGO_URI`, `MONGO_DB` для задач Airflow.

## Дополнительно

- **Перезапуск airflow** - `docker compose restart airflow`
- **Порт занят** - `docker-compose.yml` (например `8081:8080`).
- 