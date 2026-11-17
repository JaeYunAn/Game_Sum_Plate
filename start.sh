#!/usr/bin/env bash
# 번호판 더하기 실행 스크립트 (Windows Git Bash 기준)
#
#   bash start.sh           Django API + Caddy + Cloudflare Tunnel (외부 접속)
#   bash start.sh --local   Django API + Caddy 만 (이 PC에서 http://127.0.0.1:8080 으로 접속)
#
# Ctrl+C 를 누르면 함께 띄운 프로세스를 모두 종료한다.

set -u
cd "$(dirname "$0")" || exit 1

MODE="${1:-}"

fail() {
  echo "오류: $*" >&2
  exit 1
}

PYTHON="${PYTHON:-.venv/Scripts/python.exe}"
[ -x "$PYTHON" ] || PYTHON=".venv/bin/python"   # macOS / Linux
[ -x "$PYTHON" ] || fail "가상환경(.venv)이 없습니다. README 의 '설치'를 먼저 진행하세요."

command -v caddy >/dev/null 2>&1 \
  || fail "caddy 를 찾을 수 없습니다. (winget install -e --id CaddyServer.Caddy 후 Git Bash 재실행)"

CLOUDFLARED=""
if [ "$MODE" != "--local" ]; then
  CLOUDFLARED="$(command -v cloudflared 2>/dev/null || true)"
  [ -n "$CLOUDFLARED" ] || CLOUDFLARED="/c/Program Files (x86)/cloudflared/cloudflared.exe"
  [ -x "$CLOUDFLARED" ] \
    || fail "cloudflared 를 찾을 수 없습니다. (winget install -e --id Cloudflare.cloudflared) 외부 접속 없이 실행하려면 bash start.sh --local"
fi

echo "[1/3] 데이터베이스 준비"
# --fake-initial: 마이그레이션 도입 전에 만든 DB(테이블이 이미 있는 경우)도 그대로 이어서 쓴다.
"$PYTHON" backend/manage.py migrate --fake-initial --noinput \
  || fail "데이터베이스 준비에 실패했습니다. 위 메시지를 확인하세요."

PIDS=()

cleanup() {
  trap - EXIT INT TERM
  echo
  echo "종료하는 중..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null
  done
  wait 2>/dev/null
}

trap cleanup EXIT
trap 'exit 130' INT TERM

echo "[2/3] Django API(127.0.0.1:8000)와 Caddy(127.0.0.1:8080) 시작"
"$PYTHON" -m uvicorn config.asgi:application --app-dir backend --host 127.0.0.1 --port 8000 &
PIDS+=($!)

caddy run --config Caddyfile --adapter caddyfile &
PIDS+=($!)

ready=""
for _ in $(seq 1 50); do
  if curl -sf -o /dev/null http://127.0.0.1:8000/api/health; then
    ready="yes"
    break
  fi
  sleep 0.2
done
[ -n "$ready" ] || fail "Django API 가 시작되지 않았습니다. 8000번 포트를 이미 쓰고 있는지 확인하세요."

if [ "$MODE" = "--local" ]; then
  echo "[3/3] 준비 완료: http://127.0.0.1:8080  (종료: Ctrl+C)"
  wait
else
  echo "[3/3] Cloudflare Tunnel 시작: 아래에 표시되는 https://...trycloudflare.com 주소로 접속하세요. (종료: Ctrl+C)"
  "$CLOUDFLARED" tunnel --url http://127.0.0.1:8080
fi
