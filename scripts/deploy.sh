#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"

if [ ! -f .env ]; then
  echo "Missing $PROJECT_DIR/.env" >&2
  exit 1
fi

COMPOSE_FILES="-f compose.yml -f compose.prod.yml"

docker compose $COMPOSE_FILES config --quiet
docker compose $COMPOSE_FILES pull postgres caddy
docker compose $COMPOSE_FILES build --pull api worker bot frontend
docker compose $COMPOSE_FILES up -d --remove-orphans
docker compose $COMPOSE_FILES ps
