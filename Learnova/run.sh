#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APP_URL="http://localhost:8000"
DOCS_URL="http://localhost:8000/docs"
HEALTH_URL="http://localhost:8000/api/health"

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    echo "ERROR: Docker Compose is not installed."
    exit 1
  fi
}

print_help() {
  cat <<'EOF'
Learnova runner

Usage:
  ./run.sh [command]

Commands:
  up       Build and start containers (default)
  down     Stop and remove containers
  restart  Restart containers
  logs     Show app logs (follow)
  status   Show container status
  doctor   Check prerequisites and required env values
  help     Show this help
EOF
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: Missing required command: $1"
    exit 1
  fi
}

ensure_env_file() {
  if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
      cp .env.example .env
      echo "Created .env from .env.example"
      echo "Please edit .env and set MONGO_URL + SECRET_KEY before running again."
      exit 1
    fi

    echo "ERROR: .env not found and .env.example is missing."
    exit 1
  fi
}

env_value() {
  local key="$1"
  local line
  line=$(grep -E "^${key}=" .env | tail -n 1 || true)
  echo "${line#*=}"
}

validate_env() {
  local required=(MONGO_URL SECRET_KEY OLLAMA_BASE_URL OLLAMA_MODEL)
  local missing=0

  for key in "${required[@]}"; do
    local value
    value="$(env_value "$key")"
    if [[ -z "${value// /}" ]]; then
      echo "ERROR: $key is empty in .env"
      missing=1
    fi
  done

  if [[ "$missing" -ne 0 ]]; then
    echo "Please update Learnova/.env and run again."
    exit 1
  fi
}

doctor() {
  echo "Running checks..."
  require_command docker
  ensure_env_file
  validate_env

  if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running. Start Docker Desktop first."
    exit 1
  fi

  if docker compose version >/dev/null 2>&1; then
    echo "OK: docker compose available"
  elif command -v docker-compose >/dev/null 2>&1; then
    echo "OK: docker-compose available"
  else
    echo "ERROR: Docker Compose is not available."
    exit 1
  fi

  echo "OK: .env looks complete"
  echo "Doctor check passed"
}

up() {
  doctor
  compose_cmd up -d --build
  echo ""
  echo "Learnova is running"
  echo "App:    $APP_URL"
  echo "Docs:   $DOCS_URL"
  echo "Health: $HEALTH_URL"
}

down() {
  compose_cmd down
}

restart() {
  doctor
  compose_cmd up -d --build --force-recreate
  echo "Restart complete"
}

logs() {
  compose_cmd logs -f app
}

status() {
  compose_cmd ps
}

cmd="${1:-up}"

case "$cmd" in
  up)
    up
    ;;
  down)
    down
    ;;
  restart)
    restart
    ;;
  logs)
    logs
    ;;
  status)
    status
    ;;
  doctor)
    doctor
    ;;
  help|-h|--help)
    print_help
    ;;
  *)
    echo "Unknown command: $cmd"
    echo ""
    print_help
    exit 1
    ;;
esac
