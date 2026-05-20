#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/.setup/logs"
PID_DIR="$ROOT_DIR/.setup/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"
: > "$LOG_DIR/backend.log"
: > "$LOG_DIR/frontend.log"

BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

if [[ -d "/Applications/Docker.app/Contents/Resources/bin" ]]; then
  export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
fi

log_step() {
  echo ""
  echo "==> $1"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

install_with_brew_or_apt() {
  local brew_pkg="$1"
  local apt_pkg="$2"
  if command_exists brew; then
    brew install "$brew_pkg"
    return
  fi
  if command_exists apt-get; then
    sudo apt-get update
    sudo apt-get install -y "$apt_pkg"
    return
  fi
  echo "Please install $brew_pkg manually and re-run setup."
  exit 1
}

install_docker() {
  if [[ "$(uname -s)" == "Darwin" ]] && command_exists brew; then
    brew install --cask docker
    echo "Docker Desktop installed. Please open Docker Desktop once, then re-run ./setup.sh."
    exit 1
  fi
  if command_exists apt-get; then
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose-plugin
    sudo systemctl enable docker || true
    sudo systemctl start docker || true
    return
  fi
  echo "Please install Docker manually and re-run setup."
  exit 1
}

ensure_dependencies() {
  log_step "Checking system dependencies"
  if ! command_exists node; then install_with_brew_or_apt node nodejs; fi
  if ! command_exists npm; then install_with_brew_or_apt npm npm; fi
  if ! command_exists python3; then install_with_brew_or_apt python python3; fi
  if ! command_exists pip3; then install_with_brew_or_apt python python3-pip; fi
  if ! command_exists make; then install_with_brew_or_apt make make; fi
  if ! command_exists curl; then install_with_brew_or_apt curl curl; fi

  if ! command_exists docker; then
    log_step "Docker not found, installing"
    install_docker
  fi

  if ! docker compose version >/dev/null 2>&1; then
    echo "Docker Compose plugin missing. Install Docker Desktop (macOS) or docker-compose-plugin (Linux)."
    exit 1
  fi

  if ! docker info >/dev/null 2>&1; then
    echo "Docker daemon is not running. Start Docker and re-run ./setup.sh."
    exit 1
  fi
}

prepare_env_files() {
  log_step "Preparing environment files"
  cp "$ROOT_DIR/backend/.env.local" "$ROOT_DIR/backend/.env"
  [[ -f "$ROOT_DIR/frontend/.env.local" ]] || cp "$ROOT_DIR/frontend/.env.local.example" "$ROOT_DIR/frontend/.env.local"
}

install_project_dependencies() {
  log_step "Installing backend dependencies"
  cd "$ROOT_DIR/backend"
  if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
  fi
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  .venv/bin/python -m pip install -r requirements-dev.txt >/dev/null

  log_step "Installing frontend dependencies"
  cd "$ROOT_DIR/frontend"
  if [[ -f package-lock.json ]]; then
    npm ci >/dev/null
  else
    npm install >/dev/null
  fi
}

start_postgres() {
  log_step "Starting local PostgreSQL"
  cd "$ROOT_DIR"
  docker compose -f docker-compose.local.yml up -d
}

self_heal_postgres_db() {
  log_step "Ensuring local database exists"
  cd "$ROOT_DIR"
  docker compose -f docker-compose.local.yml exec -T postgres \
    psql -U postgres -d postgres -c "CREATE DATABASE health_insights_dev;" >/dev/null 2>&1 || true
  cd "$ROOT_DIR/backend"
  .venv/bin/python - <<'PY'
import psycopg2
conn = psycopg2.connect(host='127.0.0.1', port=5432, user='postgres', password='postgres', dbname='postgres')
conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT 1 FROM pg_database WHERE datname='health_insights_dev'")
if cur.fetchone() is None:
    cur.execute("CREATE DATABASE health_insights_dev")
cur.close()
conn.close()
PY
}

self_heal_db_schema() {
  log_step "Self-healing local DB schema"
  cd "$ROOT_DIR/backend"
  PYTHONPATH=. .venv/bin/python scripts/self_heal_db.py
}

wait_for_http() {
  local url="$1"
  local retries="${2:-60}"
  local sleep_sec="${3:-2}"
  for _ in $(seq 1 "$retries"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$sleep_sec"
  done
  return 1
}

cleanup_stale_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [[ -n "${pid:-}" ]] && ! kill -0 "$pid" >/dev/null 2>&1; then
      rm -f "$pid_file"
    fi
  fi
}

start_backend() {
  log_step "Starting backend service"
  cleanup_stale_pid "$BACKEND_PID_FILE"
  if [[ -f "$BACKEND_PID_FILE" ]]; then
    local old_pid
    old_pid="$(cat "$BACKEND_PID_FILE" 2>/dev/null || true)"
    if [[ -n "${old_pid:-}" ]] && kill -0 "$old_pid" >/dev/null 2>&1; then
      kill "$old_pid" || true
      sleep 1
    fi
    rm -f "$BACKEND_PID_FILE"
  elif wait_for_http "http://127.0.0.1:8000/health/live" 2 1; then
    local port_pid
    port_pid="$(lsof -ti tcp:8000 2>/dev/null || true)"
    if [[ -n "${port_pid:-}" ]]; then
      kill "$port_pid" || true
      sleep 1
    fi
  fi
  cd "$ROOT_DIR/backend"
  nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
  echo $! > "$BACKEND_PID_FILE"
  if ! wait_for_http "http://127.0.0.1:8000/health/live" 60 2; then
    echo "Backend failed to start. Check $LOG_DIR/backend.log"
    exit 1
  fi
}

start_frontend() {
  log_step "Starting frontend service"
  cleanup_stale_pid "$FRONTEND_PID_FILE"
  if wait_for_http "http://127.0.0.1:3000" 2 1; then
    echo "Frontend already running."
    return
  fi
  cd "$ROOT_DIR/frontend"
  nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
  echo $! > "$FRONTEND_PID_FILE"
  if ! wait_for_http "http://127.0.0.1:3000" 90 2; then
    echo "Frontend failed to start. Check $LOG_DIR/frontend.log"
    exit 1
  fi
}

seed_demo_data() {
  log_step "Seeding demo database data"
  cd "$ROOT_DIR"
  make local-seed-reseed
}

verify_core_endpoints() {
  log_step "Verifying backend and frontend endpoints"
  curl -fsS "http://127.0.0.1:8000/health/live" >/dev/null
  curl -fsS "http://127.0.0.1:8000/health/ready" >/dev/null
  curl -fsS "http://127.0.0.1:3000/platform/dashboard" >/dev/null
  curl -fsS "http://127.0.0.1:3000/platform/timeline" >/dev/null
  curl -fsS "http://127.0.0.1:3000/platform/insights" >/dev/null
  curl -fsS "http://127.0.0.1:3000/platform/actions" >/dev/null
  curl -fsS "http://127.0.0.1:3000/platform/weekly-report" >/dev/null
  curl -fsS "http://127.0.0.1:3000/platform/analytics" >/dev/null
}

verify_dashboard_api_with_demo_login() {
  log_step "Verifying /api/v1/dashboard using demo account"
  python3 - <<'PY'
import json
import urllib.request

base = "http://127.0.0.1:8000"
payload = json.dumps({"email": "demo@health.example.com", "password": "Demo1234!"}).encode()
req = urllib.request.Request(
    f"{base}/api/v1/auth/login",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=15) as resp:
    token = json.loads(resp.read().decode())["access_token"]

persons_req = urllib.request.Request(
    f"{base}/api/v1/persons",
    headers={"Authorization": f"Bearer {token}"},
)
with urllib.request.urlopen(persons_req, timeout=15) as resp:
    persons = json.loads(resp.read().decode())
person_id = persons[0]["id"]

dashboard_req = urllib.request.Request(
    f"{base}/api/v1/dashboard?person_id={person_id}",
    headers={"Authorization": f"Bearer {token}"},
)
with urllib.request.urlopen(dashboard_req, timeout=15) as resp:
    data = json.loads(resp.read().decode())
assert "health_score" in data
print("dashboard_api_ok")
PY
}

finish_message() {
  log_step "Setup completed"
  echo "Backend:  http://localhost:8000/docs"
  echo "Frontend: http://localhost:3000/platform/dashboard"
  echo "Next: open http://localhost:3000/platform/demo-bootstrap and click 'Seed Demo Client Data'"
  echo "Logs: $LOG_DIR"
}

main() {
  ensure_dependencies
  prepare_env_files
  install_project_dependencies
  start_postgres
  self_heal_postgres_db
  self_heal_db_schema
  start_backend
  seed_demo_data
  start_frontend
  verify_core_endpoints
  verify_dashboard_api_with_demo_login
  finish_message
}

main "$@"
