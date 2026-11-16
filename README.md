# 번호판 더하기 실행 방법

Windows + Git Bash 기준입니다. 아래 순서대로 실행하면 됩니다.

## 1. 최초 1회 설치

Git Bash에서 실행합니다.

```bash
winget install -e --id CaddyServer.Caddy
winget install -e --id Cloudflare.cloudflared
```

설치가 끝나면 Git Bash를 다시 실행합니다. Python 3.12와 Git도 설치되어 있어야 합니다.

## 2. 프로젝트 받기

`<저장소 주소>`를 실제 Git 저장소 주소로 바꿔 실행합니다.

```bash
git clone <저장소 주소>
cd <프로젝트 폴더>
```

## 3. 가상환경 및 패키지 설치

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
```

## 4. 데이터베이스 최초 생성

처음 실행할 때 한 번만 실행합니다. 기존 DB가 있으면 데이터를 삭제하지 않습니다.

```bash
python - <<'PY'
import sqlite3

with sqlite3.connect("number_addition.db") as db:
    db.execute("PRAGMA journal_mode = WAL")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nickname TEXT NOT NULL UNIQUE,
        token_hash TEXT NOT NULL UNIQUE,
        created_at INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS records (
        id TEXT PRIMARY KEY,
        member_id INTEGER,
        nickname TEXT NOT NULL,
        duration INTEGER NOT NULL,
        game_mode TEXT NOT NULL,
        correct INTEGER NOT NULL,
        wrong INTEGER NOT NULL,
        accuracy REAL NOT NULL,
        score INTEGER NOT NULL,
        average_response_time REAL NOT NULL,
        created_at INTEGER NOT NULL,
        FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE SET NULL
    );

    CREATE INDEX IF NOT EXISTS idx_records_ranking
    ON records (duration, game_mode, score DESC, accuracy DESC,
                average_response_time ASC, created_at ASC);
    """)

print("데이터베이스 준비 완료")
PY
```

## 5. 서버 실행

Git Bash 창을 3개 열고, 각 창에서 프로젝트 폴더로 이동합니다.

**창 1 — Django API**

```bash
source .venv/Scripts/activate
.venv/Scripts/python.exe -m uvicorn config.asgi:application --app-dir backend --host 127.0.0.1 --port 8000
```

**창 2 — Caddy**

```bash
CADDY_BIN="$(command -v caddy)"
"$CADDY_BIN" run --config Caddyfile --adapter caddyfile
```

**창 3 — 외부 접속**

```bash
cloudflared tunnel --url http://127.0.0.1:8080
```

창 3에 표시되는 `https://...trycloudflare.com` 주소로 접속합니다. 세 창은 접속 중 계속 켜 두어야 합니다. 종료하려면 각 창에서 `Ctrl + C`를 누릅니다.
