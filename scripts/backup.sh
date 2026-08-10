#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"

if [ ! -f .env ]; then
  echo "Missing $PROJECT_DIR/.env" >&2
  exit 1
fi

set -a
. ./.env
set +a

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"

BACKUP_DIR=${BACKUP_DIR:-"$PROJECT_DIR/backups"}
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-14}
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)

mkdir -p "$BACKUP_DIR"

docker compose -f compose.yml -f compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$BACKUP_DIR/postgres-$TIMESTAMP.sql.gz"

docker compose -f compose.yml -f compose.prod.yml exec -T worker \
  tar -cf - -C /data/uploads . | gzip > "$BACKUP_DIR/uploads-$TIMESTAMP.tar.gz"

find "$BACKUP_DIR" -type f -mtime "+$BACKUP_RETENTION_DAYS" -delete

echo "Backup created in $BACKUP_DIR"
