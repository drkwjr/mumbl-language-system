#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME=${CONTAINER_NAME:-mumbl-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-mumbl}
POSTGRES_USER=${POSTGRES_USER:-mumbl}
POSTGRES_DB=${POSTGRES_DB:-mumbl_lang_system}
POSTGRES_PORT=${POSTGRES_PORT:-5432}

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for local bootstrap" >&2
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    docker start "${CONTAINER_NAME}" >/dev/null
  else
    docker run -d \
      --name "${CONTAINER_NAME}" \
      -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
      -e POSTGRES_USER="${POSTGRES_USER}" \
      -e POSTGRES_DB="${POSTGRES_DB}" \
      -p "${POSTGRES_PORT}:5432" \
      postgres:16 >/dev/null
  fi
fi

echo "Waiting for Postgres to be ready..."
until docker exec "${CONTAINER_NAME}" pg_isready -U "${POSTGRES_USER}" >/dev/null 2>&1; do
  sleep 1
  printf '.'
done
printf '\n'

docker exec -i "${CONTAINER_NAME}" psql \
  -U "${POSTGRES_USER}" \
  -d "${POSTGRES_DB}" \
  -c "CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP);"

is_migration_applied() {
  local name="$1"
  docker exec -i "${CONTAINER_NAME}" psql \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -tAc "SELECT 1 FROM schema_migrations WHERE filename='${name}' LIMIT 1;" | tr -d '[:space:]'
}

mark_migration_applied() {
  local name="$1"
  docker exec -i "${CONTAINER_NAME}" psql \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -c "INSERT INTO schema_migrations (filename) VALUES ('${name}') ON CONFLICT DO NOTHING;" >/dev/null
}

bootstrap_if_present() {
  local name="$1"
  local check_table="$2"
  if [[ -z "${check_table}" ]]; then
    return 1
  fi
  local exists
  exists=$(docker exec -i "${CONTAINER_NAME}" psql \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -tAc "SELECT to_regclass('public.${check_table}');" | tr -d '[:space:]')
  if [[ "${exists}" == "${check_table}" ]]; then
    mark_migration_applied "${name}"
    return 0
  fi
  return 1
}

MIGRATIONS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../infra/db/migrations" && pwd)"

for migration in "${MIGRATIONS_DIR}"/*.sql; do
  if [[ "${migration}" == *"_down.sql" ]]; then
    continue
  fi
  migration_name="${migration##*/}"
  applied=$(is_migration_applied "${migration_name}")
  if [[ "${applied}" == "1" ]]; then
    echo "Skipping ${migration_name} (already applied)"
    continue
  fi

  if [[ "${migration_name}" == "001_initial_schema.sql" ]]; then
    if bootstrap_if_present "${migration_name}" "text_segments"; then
      echo "Skipping ${migration_name} (existing schema detected)"
      continue
    fi
  elif [[ "${migration_name}" == "002_radio_ingestion_schema.sql" ]]; then
    if bootstrap_if_present "${migration_name}" "radio_sources"; then
      echo "Skipping ${migration_name} (existing schema detected)"
      continue
    fi
  elif [[ "${migration_name}" == "003_segment_language_verifications.sql" ]]; then
    if bootstrap_if_present "${migration_name}" "segment_language_verifications"; then
      echo "Skipping ${migration_name} (existing schema detected)"
      continue
    fi
  elif [[ "${migration_name}" == "004_pipeline_events.sql" ]]; then
    if bootstrap_if_present "${migration_name}" "pipeline_events"; then
      echo "Skipping ${migration_name} (existing schema detected)"
      continue
    fi
  elif [[ "${migration_name}" == "005_station_frequency_candidates.sql" ]]; then
    if bootstrap_if_present "${migration_name}" "station_frequency_candidates"; then
      echo "Skipping ${migration_name} (existing schema detected)"
      continue
    fi
  fi
  echo "Applying ${migration##*/}"
  docker exec -i "${CONTAINER_NAME}" psql \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    < "${migration}"
  mark_migration_applied "${migration_name}"
done

echo "Local Postgres ready."
cat <<ENVVARS

Export these for the API:
export DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}

Then run discovery:
python -m radio_ingestion.discovery.radio_browser --country SO --limit 5
ENVVARS
