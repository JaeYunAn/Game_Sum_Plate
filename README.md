# 번호판 더하기

자동차 번호판의 뒤 네 자리 숫자를 빠르게 더하는 웹 게임입니다. 회원으로 로그인해 플레이하면 기록이 명예의 전당(순위표)에 올라갑니다.

## 게임 규칙

| 구분 | 내용 |
|---|---|
| 점수모드 | 1분 동안, 문제당 5초 안에 답합니다. 시작 전 3초 카운트다운, 문제 사이 1초 텀이 있습니다. 게임 시간은 1분으로 고정입니다. |
| 점수 | 정답 +10점, 오답·시간 초과 −20점 |
| 어려운 문제 | 빨리 푸는 지름길이 없는 번호판. 정답 +15점, 오답·시간 초과 −10점 (아래 설명 참고) |
| 생존모드 | 50점으로 시작해 점수가 0점 이하가 되면 끝납니다. 점수 규칙은 점수모드와 같습니다. 문제당 제한 시간은 5초에서 시작해 게임 시간 15초마다 0.5초씩 줄어 1초까지 내려갑니다. 버틴 시간이 기록입니다. |
| 연습 | 시간 제한과 점수 없이 정답까지 걸린 시간만 잽니다. 기록은 남지 않습니다. |
| 기록 저장 | 로그인한 상태로 시작해 끝까지 진행한 점수모드·생존모드 게임만 저장됩니다. 중도 종료한 게임과 게스트 게임은 저장되지 않습니다. |
| 명예의 전당 | 모드별 TOP 10. 회원별 최고 기록 하나만 올라갑니다. 점수모드는 점수 → 정답률 → 평균 응답 시간 → 먼저 세운 기록 순, 생존모드는 생존 시간 → 정답 수 → 먼저 세운 기록 순입니다. |
| 입력 | PC는 숫자를 입력하고 Enter 또는 제출 버튼. 터치 기기는 화면의 숫자 키패드로 입력합니다. |
| 결과 | 점수모드는 점수와 정답률, 생존모드는 생존 시간과 최고 점수를 보여 줍니다. 틀린 문제(번호판·풀이·내 답) 목록도 함께 나옵니다. |

### 어려운 문제

아래 네 가지를 모두 만족하는 번호판입니다(예: `5789`). 각 조건은 빨리 푸는 지름길을 하나씩 막습니다.

| 조건 | 막는 지름길 |
|---|---|
| 0이 없다 | 더할 숫자가 줄어든다 (`0389`는 세 숫자만 더하면 된다) |
| 네 숫자가 모두 다르다 | 곱셈으로 풀린다 (`9998` = 9×3 + 8) |
| 더해서 10이 되는 짝이 없다 | 10 만들기 (`3764` = 10 + 10) |
| 합이 20 이상이다 | 작은 숫자뿐이라 받아올림이 거의 없다 (`1234`). 세 숫자로 10이 되는 조합도 함께 빠진다 |

10000개 조합 중 648개(6.5%)가 해당하며, 숫자 구성으로는 27가지입니다. 1분 게임에서 평균 한 문제쯤 나옵니다.

### 생존모드의 게임 시간

생존모드의 게임 시간은 **응답 시간과 문제 사이 텀(1초)을 더한 값**입니다. 실제 시계가 아니라 답안 기록으로 계산하므로 브라우저와 서버가 ms 단위까지 같은 값을 얻습니다. 문제의 제한 시간은 그 문제가 나온 게임 시간으로 정해집니다(0~15초 5.0초, 15~30초 4.5초, … 120초 이후 1.0초).

규칙 값은 화면 표시용으로 `app.js`의 `RULES`에, 실제 채점용으로 `backend/game_api/game_rules.py`에 있습니다. 규칙을 바꿀 때는 두 곳을 함께 고치고, 화면의 "게임 방법" 문구(`index.html`)도 맞춰야 합니다.

## 구조

```text
브라우저
   │  https://....trycloudflare.com (Cloudflare Tunnel) 또는 http://127.0.0.1:8080
   ▼
Caddy :8080            ── /, /index.html, /app.js, /style.css 만 정적 제공 (그 외 경로는 404)
   │  /api/*
   ▼
Django REST framework :8000 (uvicorn)
   ▼
SQLite  number_addition.db
```

| 경로 | 역할 |
|---|---|
| `index.html`, `app.js`, `style.css` | 프론트엔드 (프레임워크 없음) |
| `backend/config/` | Django 설정 |
| `backend/game_api/` | API: 회원, 게임 시작, 기록 저장·조회 |
| `backend/game_api/game_rules.py` | 게임 규칙과 서버 채점 |
| `backend/game_api/migrations/` | DB 스키마 (Django 마이그레이션) |
| `backend/game_api/tests.py` | API 테스트 |
| `Caddyfile` | 정적 파일 제공, `/api/*` 프록시, 보안·캐시 헤더 |
| `start.sh` | 실행 스크립트 |

## 설치 (최초 1회)

Windows + Git Bash 기준입니다. Python 3.12와 Git이 설치되어 있어야 합니다.

```bash
winget install -e --id CaddyServer.Caddy
winget install -e --id Cloudflare.cloudflared
```

설치가 끝나면 Git Bash를 다시 실행한 뒤 프로젝트 폴더에서 가상환경을 만듭니다.

```bash
git clone <저장소 주소>
cd <프로젝트 폴더>

python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
```

## 실행

```bash
bash start.sh
```

DB 준비(마이그레이션) → Django API → Caddy → Cloudflare Tunnel 순서로 실행합니다. 화면에 표시되는 `https://...trycloudflare.com` 주소로 접속하면 됩니다. `Ctrl + C`를 누르면 모두 종료됩니다.

외부 접속 없이 이 PC에서만 쓰려면 `bash start.sh --local`로 실행하고 `http://127.0.0.1:8080`으로 접속합니다.

<details>
<summary>스크립트 없이 직접 실행하기</summary>

Git Bash 창 3개에서 각각 프로젝트 폴더로 이동한 뒤 실행합니다.

```bash
# 최초 1회, 그리고 코드를 새로 받은 뒤: DB 준비
.venv/Scripts/python.exe backend/manage.py migrate --fake-initial

# 창 1: Django API
.venv/Scripts/python.exe -m uvicorn config.asgi:application --app-dir backend --host 127.0.0.1 --port 8000

# 창 2: Caddy
caddy run --config Caddyfile --adapter caddyfile

# 창 3: 외부 접속
cloudflared tunnel --url http://127.0.0.1:8080
```

</details>

### 참고

- **DB 파일**: `number_addition.db`는 처음 실행할 때 자동으로 만들어집니다. 회원 닉네임과 인증 정보가 들어 있으므로 Git에 올리지 않습니다(`.gitignore` 대상).
- **기존 DB에서 올라오는 경우**: 마이그레이션 도입 전에 쓰던 `number_addition.db`가 있으면 그대로 두고 실행하면 됩니다. `migrate --fake-initial`이 기존 테이블과 데이터를 유지한 채 필요한 변경만 적용합니다. 실행 전에 DB 파일을 백업해 두세요. 영문 대소문자만 다른 닉네임(예: `Tester`, `tester`)이 이미 있으면 안내 메시지와 함께 중단되며, 한쪽을 정리한 뒤 다시 실행하면 됩니다.
- **30초 게임 기록**: 점수모드가 1분 고정으로 바뀌기 전에 저장된 30초 게임 기록은 DB에는 남아 있지만 순위표에는 나오지 않습니다.
- **기존 회원의 비밀번호**: 비밀번호 도입 전에 가입한 회원은 다음 로그인 때 입력한 비밀번호가 그 계정의 비밀번호로 설정됩니다. 회원들에게 한 번씩 로그인해 비밀번호를 정하도록 안내하세요.
- **접속 주소**: Quick Tunnel 주소는 실행할 때마다 바뀝니다. 고정 주소가 필요하면 Cloudflare 계정과 도메인으로 이름 있는 터널(named tunnel)을 만들어야 합니다.
- **SECRET_KEY**: 처음 실행할 때 `.django_secret_key` 파일로 자동 생성됩니다. 환경변수 `DJANGO_SECRET_KEY`로 지정할 수도 있습니다.
- **환경변수**: `NUMBER_ADDITION_DB_PATH`(DB 파일 위치), `DJANGO_ALLOWED_HOSTS`(쉼표로 구분), `DJANGO_DEBUG`(`true`면 디버그 모드)

## 테스트

```bash
.venv/Scripts/python.exe backend/manage.py test game_api
```

테스트는 메모리 DB를 쓰므로 `number_addition.db`를 건드리지 않습니다.

## API

오류 응답은 모두 `{"detail": "메시지"}` 형식입니다. 인증이 필요한 요청은 `Authorization: Bearer <token>` 헤더를 보냅니다.

| Method | Path | 인증 | 설명 |
|---|---|---|---|
| GET | `/api/health` | | 서버 상태 |
| POST | `/api/register` | | 회원가입 `{nickname, password}` → `{id, nickname, hasPassword, token}` |
| POST | `/api/login` | | 로그인 `{nickname, password}` → 새 토큰 발급(기존 토큰은 무효) |
| GET | `/api/me` | 필요 | 현재 회원 |
| POST | `/api/logout` | 필요 | 토큰 무효화 |
| DELETE | `/api/account` | 필요 | 회원탈퇴 `{password}`. 기록은 남고 순위표에 `(탈퇴)`로 표시 |
| POST | `/api/games` | 필요 | 게임 시작 `{gameMode}` (`score` 또는 `survival`) → `{gameId, duration, gameMode, questions}` |
| POST | `/api/records` | 필요 | 기록 저장 `{gameId, answers: [{answer, time}]}` |
| GET | `/api/records?gameMode=score` | | 순위표 TOP 10 (회원별 최고 기록). `gameMode=survival`이면 생존모드 순위표 |

기록 응답에는 `score`, `accuracy`, `correct`, `wrong`, `averageResponseTime`, `survivalTime` 등이 들어 있습니다. 생존모드 기록은 `survivalTime`(초)이 버틴 시간이고 `score`는 게임 중 최고 점수, `duration`은 0입니다. 점수모드 기록의 `survivalTime`은 `null`입니다.

### 기록이 저장되는 과정

1. 회원이 점수모드나 생존모드 게임을 시작하면 서버가 문제를 발급하고 시작 시각을 기록합니다(`/api/games`).
2. 게임이 끝나면 브라우저는 점수나 생존 시간이 아니라 **문제별로 입력한 답과 걸린 시간**을 보냅니다(`/api/records`).
3. 서버는 발급했던 문제로 직접 채점해 점수와 생존 시간을 계산합니다.
   - 점수모드: 게임 시간이 다 지나기 전의 요청, 게임 시간 안에 불가능한 문제 수는 거부합니다.
   - 생존모드: 탈락하기 전의 기록, 탈락한 뒤의 답안이 있는 기록, 게임을 시작한 뒤 실제로 지난 시간보다 오래 버텼다는 기록은 거부합니다.
   - 같은 게임은 한 번만 저장할 수 있습니다.

브라우저에서 진행되는 게임이라 답을 자동으로 입력하는 프로그램까지 막지는 못합니다. 요청 내용을 고쳐 임의의 점수를 올리는 것을 막는 수준입니다.

### 요청 횟수 제한

로그인(접속 IP당 분당 10회, 닉네임당 시간당 30회), 회원가입(IP당 시간당 10회) 등에 제한이 있습니다. 값은 `backend/config/settings.py`의 `DEFAULT_THROTTLE_RATES`에서 바꿉니다.
