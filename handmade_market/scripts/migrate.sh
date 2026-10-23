#!/usr/bin/env bash
# Применяет миграции PostgreSQL из папки migrations/ к БД docker-compose.
#
# Использование:
#   ./scripts/migrate.sh up     # применить все *.up.sql по порядку
#   ./scripts/migrate.sh down   # откатить все *.down.sql (в обратном порядке)
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER="${DB_CONTAINER:-handmade-market-pg}"
DB_NAME="${DB_NAME:-handmade_market}"
DB_USER="${DB_USER:-postgres}"
ACTION="${1:-up}"

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  echo "Контейнер ${CONTAINER} не запущен. Сначала: docker compose up -d db"
  exit 1
fi

shopt -s nullglob
files=("${DIR}"/migrations/*."${ACTION}".sql)
if [ "${#files[@]}" -eq 0 ]; then
  echo "Нет файлов *.${ACTION}.sql в migrations/"
  exit 1
fi

# down-миграции выполняем в обратном порядке (от последней к первой).
if [ "$ACTION" = "down" ]; then
  reversed=()
  for (( i = ${#files[@]} - 1; i >= 0; i-- )); do
    reversed+=("${files[$i]}")
  done
  files=("${reversed[@]}")
fi

for f in "${files[@]}"; do
  echo "==> ${ACTION}: $(basename "$f")"
  docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 < "$f"
done

echo "Готово (${ACTION})"
