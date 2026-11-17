# 번호판 더하기 프로젝트: Django REST framework 백엔드 교체 작업지침

> **이 문서는 지난 작업의 기록입니다.** FastAPI에서 DRF로의 교체는 완료되었고, 이후 스키마 관리(마이그레이션), 로그인 방식(비밀번호), 기록 저장 API(서버 채점)가 바뀌어 아래 내용은 현재 코드와 다릅니다. `server.py`도 삭제되었습니다. 현재 구조와 API는 `README.md`와 `작업상황_체크포인트.md`를 보세요.

작성 기준일: 2026-11-16  
목적: 기존 FastAPI 백엔드를 Django REST framework(DRF) 기반의 순수 API 백엔드로 교체한다. 새 대화에서는 이 문서를 기준으로 실제 교체 작업을 시작한다.

---

## 1. 작업 목표

현재 FastAPI가 담당하는 회원 관리, 인증, 게임 기록 저장 및 조회 기능을 Django REST framework로 이전한다.

최종 목표는 다음과 같다.

- 백엔드는 Django + Django REST framework만 API 처리에 사용한다.
- Django 템플릿으로 화면을 만들거나 기존 HTML을 수정하지 않는다.
- 기존 `index.html`, `app.js`, `style.css`의 게임 화면과 게임 로직을 보존한다.
- 기존 API 경로, 요청 형식, 응답 형식, 인증 헤더를 가능한 한 그대로 유지한다.
- 기존 `number_addition.db`를 그대로 사용한다.
- 기존 회원과 게임 기록을 삭제하거나 초기화하지 않는다.
- 서버 운영 시 기존 Cloudflare Tunnel을 계속 활용한다.
- 교체가 끝나고 검증될 때까지 기존 `server.py`를 삭제하거나 덮어쓰지 않는다.

이번 대화에서는 코드 수정, 패키지 설치, 데이터베이스 변경을 하지 않았다. 현재까지 확인한 정보만 정리했다.

## 2. 프로젝트 환경

프로젝트 경로:

`C:/Users/SSAFY/Desktop/minjun/밍듀니/my/숫자더하기`

Git Bash에서 확인된 경로:

`/c/Users/SSAFY/Desktop/minjun/밍듀니/my/숫자더하기`

개발 환경:

- 운영체제: Windows
- 터미널: Git Bash
- Python: 3.12.7
- 가상환경: `.venv`
- 기존 백엔드: FastAPI + Uvicorn
- 데이터베이스: SQLite
- 프론트엔드: HTML, CSS, JavaScript
- 외부 접속: Cloudflare Quick Tunnel

주요 파일:

- `index.html`
- `app.js`
- `style.css`
- `server.py`
- `requirements.txt`
- `.gitignore`
- `number_addition.db`
- `번호판 더하기 실행.bat`
- `외부접속_실행방법.md`
- `작업체크포인트.txt`
- `README.txt`
- `메모장.md`

현재 `requirements.txt`:

```text
fastapi>=0.115,<1.0
uvicorn>=0.30,<1.0
```

현재 가상환경에는 FastAPI와 Uvicorn이 설치되어 있다. `httpx`는 설치되어 있지 않다.

## 3. 기존 Git 변경사항 보존

확인 당시 `git status --short`에 다음 파일이 수정된 상태로 표시되었다.

- `app.js`
- `index.html`
- `server.py`
- `style.css`
- `작업체크포인트.txt`

확인 당시 `git diff --stat`:

```text
app.js                  |  82 +++
index.html              |  13 +
server.py               |  51 +-
style.css               |  14 +-
작업체크포인트.txt       | 609 ++++++++++++++++++---
```

이 변경사항은 이번 DRF 사전 분석 이전부터 존재했다. 새 대화에서는 다음 작업을 절대 하지 않는다.

- `git checkout -- .`
- `git reset --hard`
- `git clean -fd`
- 수정 파일 전체 덮어쓰기
- 사용자가 요청하지 않은 변경사항 되돌리기

기존 변경사항을 먼저 보존하고, 새로 만드는 파일과 수정하는 파일을 구분한다.

## 4. 현재 백엔드 구조

현재 `server.py`는 다음 기능을 포함한다.

- SQLite 연결 및 트랜잭션 처리
- `members`, `records` 테이블 생성 확인
- 회원가입
- 닉네임 로그인
- Bearer 토큰 인증
- 회원 상태 조회
- 로그아웃
- 회원탈퇴
- 게임 기록 저장
- 게임 기록 조회 및 TOP 10 정렬
- 상태 확인
- HTML, JavaScript, CSS 파일 제공

주요 함수 및 API 위치:

- `database()`
- `init_database()`
- `RegisterRequest`
- `LoginRequest`
- `RecordRequest`
- `hash_token()`
- `get_current_member()`
- `POST /api/register`
- `POST /api/login`
- `GET /api/me`
- `POST /api/logout`
- `DELETE /api/account`
- `POST /api/records`
- `GET /api/records`
- `GET /api/health`
- `GET /`, `GET /app.js`, `GET /style.css`

중요한 구조적 특징:

현재 FastAPI는 API뿐 아니라 `/`, `/app.js`, `/style.css` 요청으로 프론트엔드 파일도 직접 제공한다. DRF로 이전할 때 이 역할을 Django에 넣지 않는 것이 목표다.

## 5. 데이터베이스 현황

데이터베이스 파일:

`number_addition.db`

확인 당시 데이터:

- members: 2개
- records: 8개
- `PRAGMA integrity_check`: `ok`

데이터 개수는 확인 시점의 값이며 이후 게임 이용에 따라 달라질 수 있다.

### 5-1. members 테이블

```sql
CREATE TABLE members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nickname TEXT NOT NULL COLLATE NOCASE UNIQUE,
    token_hash TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL
);
```

필드 의미:

- `id`: 회원 고유 ID
- `nickname`: 닉네임, 대소문자 구분 없는 UNIQUE
- `token_hash`: 현재 유효한 인증 토큰의 SHA-256 해시, UNIQUE
- `created_at`: 가입 시간, Unix 밀리초 정수

### 5-2. records 테이블

```sql
CREATE TABLE records (
    id TEXT PRIMARY KEY,
    member_id INTEGER,
    nickname TEXT NOT NULL,
    duration INTEGER NOT NULL,
    difficulty TEXT NOT NULL,
    correct INTEGER NOT NULL,
    wrong INTEGER NOT NULL,
    accuracy REAL NOT NULL,
    score INTEGER NOT NULL,
    average_response_time REAL NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (member_id)
        REFERENCES members(id)
        ON DELETE SET NULL
);
```

필드 의미:

- `id`: UUID 문자열
- `member_id`: 회원 ID, NULL 허용
- `nickname`: 기록 당시 닉네임
- `duration`: 게임 시간
- `difficulty`: 난이도
- `correct`: 정답 수
- `wrong`: 오답 수
- `accuracy`: 정답률
- `score`: 점수
- `average_response_time`: 평균 응답 시간
- `created_at`: 기록 생성 시간, Unix 밀리초 정수

### 5-3. 인덱스 및 외래 키

`members`:

- 닉네임 UNIQUE 인덱스
- 토큰 해시 UNIQUE 인덱스

`records`:

- `idx_records_ranking` 존재
- 정렬용 컬럼: `duration`, `difficulty`, `score DESC`, `accuracy DESC`, `average_response_time ASC`, `created_at ASC`
- `member_id`는 `members.id`를 참조
- 회원 삭제 시 `records.member_id`는 NULL이 되며 기록 자체는 유지됨

SQLite 연결 관련 기존 설정:

- Foreign Key 활성화
- WAL 모드
- Busy Timeout 10초

### 5-4. 데이터베이스 이전 원칙

기존 테이블을 새 Django 모델에 맞춰 재생성하지 않는다.

권장 방식:

- 기존 DB 파일을 그대로 Django `DATABASES` 설정에 연결한다.
- 기존 테이블을 매핑하는 Django 모델은 `managed = False`로 지정한다.
- 테이블명과 컬럼명을 기존 스키마에 맞춘다.
- 기존 데이터에 대한 `migrate`, `flush`, 테이블 삭제, 테이블 재생성을 하지 않는다.
- Django 기본 User 테이블로 기존 `members`를 대체하지 않는다.
- 별도의 `db.sqlite3`를 새로 만들어 기존 DB 대신 사용하지 않는다.

기존 DB를 열기 전 서버를 종료하고 SQLite 백업 API를 사용해 별도 백업 파일을 만든다. WAL 사용 중인 DB를 서버 실행 상태에서 파일 탐색기로 단순 복사하는 방식은 피한다.

백업 전후 및 이전 후에는 다음을 확인한다.

- `members`, `records` 개수
- `PRAGMA integrity_check`
- `PRAGMA foreign_key_check`
- 테이블 및 인덱스 구조

## 6. 현재 API 계약

프론트엔드와의 호환성을 위해 아래 API 경로, 메서드, 인증 방식, JSON 필드명을 유지한다.

| 메서드 | 경로 | 인증 | 기능 |
|---|---|---|---|
| GET | `/api/health` | 불필요 | 서버 상태 |
| POST | `/api/register` | 불필요 | 회원가입 |
| POST | `/api/login` | 불필요 | 닉네임 로그인 |
| GET | `/api/me` | 필요 | 현재 회원 확인 |
| POST | `/api/logout` | 필요 | 로그아웃 및 토큰 무효화 |
| DELETE | `/api/account` | 필요 | 회원탈퇴 |
| POST | `/api/records` | 필요 | 게임 기록 저장 |
| GET | `/api/records` | 불필요 | TOP 10 기록 조회 |

기존 API 경로에 후행 슬래시(`/`)를 임의로 추가하지 않는다. 예를 들어 `/api/login`을 `/api/login/`으로 바꾸지 않는다.

### 6-1. 회원가입

요청:

```json
{
  "nickname": "닉네임"
}
```

규칙:

- 앞뒤 공백 제거
- 1~16자
- 닉네임 중복 불가
- 대소문자 구분 없이 중복 처리
- 비밀번호 없음

성공 응답: HTTP 201

```json
{
  "id": 1,
  "nickname": "닉네임",
  "token": "발급된_원본_토큰"
}
```

### 6-2. 로그인

요청:

```json
{
  "nickname": "기존회원닉네임"
}
```

규칙:

- 등록되지 않은 닉네임은 로그인 거부
- 성공 시 새 무작위 토큰 발급
- 새 토큰의 SHA-256 해시를 `members.token_hash`에 저장
- 기존 토큰은 무효화

성공 응답: HTTP 200

```json
{
  "id": 1,
  "nickname": "닉네임",
  "token": "새로_발급된_원본_토큰"
}
```

### 6-3. 현재 회원 확인

요청 헤더:

```text
Authorization: Bearer <token>
```

성공 응답: HTTP 200

```json
{
  "id": 1,
  "nickname": "닉네임"
}
```

### 6-4. 로그아웃

요청:

```text
POST /api/logout
Authorization: Bearer <token>
```

성공 응답: HTTP 200

```json
{
  "message": "로그아웃되었습니다."
}
```

기존 토큰을 더 이상 인증에 사용할 수 없도록 한다. 기존 구현은 `token_hash`를 새로운 임의 값의 해시로 교체하여 기존 토큰을 무효화한다.

### 6-5. 회원탈퇴

요청:

```text
DELETE /api/account
Authorization: Bearer <token>
```

성공 응답: HTTP 200

```json
{
  "message": "회원탈퇴가 완료되었습니다."
}
```

회원 행은 삭제하되 기존 게임 기록은 보존한다. 외래 키 동작에 따라 기존 기록의 `member_id`는 NULL이 된다. `records.nickname`은 유지한다.

### 6-6. 게임 기록 저장

요청 헤더:

```text
Content-Type: application/json
Authorization: Bearer <token>
```

요청 JSON:

```json
{
  "duration": 60,
  "difficulty": "normal",
  "correct": 10,
  "wrong": 2,
  "accuracy": 83.333333,
  "score": 60,
  "averageResponseTime": 1.25
}
```

검증 규칙:

- `duration`: 30 또는 60
- `difficulty`: `easy`, `normal`, `hard`, `extreme`
- `correct`: 0 이상 정수
- `wrong`: 0 이상 정수
- `accuracy`: 0~100
- `score`: 정수
- `averageResponseTime`: 0 이상 숫자

성공 응답: HTTP 201

```json
{
  "id": "UUID 문자열",
  "nickname": "회원 닉네임",
  "duration": 60,
  "difficulty": "normal",
  "correct": 10,
  "wrong": 2,
  "accuracy": 83.333333,
  "score": 60,
  "averageResponseTime": 1.25,
  "createdAt": 1790000000000
}
```

`averageResponseTime`, `createdAt`은 프론트엔드와의 호환성을 위해 camelCase를 유지한다. DB 컬럼은 각각 `average_response_time`, `created_at`이다.

### 6-7. 게임 기록 조회

요청 예:

```text
GET /api/records?duration=60&difficulty=normal
```

규칙:

- 인증 불필요
- `duration` 기본값 60, 허용값 30 또는 60
- `difficulty` 기본값 `normal`
- 점수 내림차순
- 정답률 내림차순
- 평균 응답 시간 오름차순
- 생성 시간 오름차순
- 최대 10개 반환

응답은 기록 객체의 배열이며, 저장 응답과 같은 JSON 필드명을 사용한다.

### 6-8. 오류 응답 형식

기존 프론트엔드는 오류 발생 시 `data.detail`을 읽는다. DRF의 기본 Serializer 오류 응답을 그대로 사용하면 프론트엔드가 오류 메시지를 읽지 못할 수 있다.

따라서 주요 오류 응답도 다음 구조를 유지한다.

```json
{
  "detail": "사용자에게 표시할 오류 메시지"
}
```

기존 상태 코드도 가능한 한 유지한다.

- 중복 닉네임: 409
- 인증 누락 또는 토큰 불일치: 401
- 입력값 오류: 기존 FastAPI 동작을 확인해 400 또는 422로 일관되게 결정

상태 코드와 응답 형식을 바꿔야 한다면 `app.js` 변경 필요성을 먼저 검토한다. 임의로 바꾸지 않는다.

## 7. 인증 구조 및 주의사항

현재 인증 방식:

- 닉네임만으로 로그인
- 비밀번호 없음
- `secrets.token_urlsafe(32)`로 무작위 토큰 생성
- SHA-256으로 토큰 해시 생성
- DB에는 원본 토큰이 아닌 해시 저장
- 브라우저에는 원본 토큰을 localStorage에 저장
- 요청 시 `Authorization: Bearer <token>` 전달
- 회원별로 `token_hash` 하나만 저장

DRF에서는 Django 기본 로그인 화면이나 기본 `TokenAuthentication`의 `Token` 접두어로 변경하지 않는다. 기존 `Bearer` 형식과 SHA-256 검증을 유지하는 사용자 정의 DRF Authentication 클래스를 구현한다.

DRF 기본 SessionAuthentication, BasicAuthentication을 임의로 활성화하지 않는다. API별로 `AllowAny`와 인증 필요 권한을 정확히 지정한다.

현재 로그인 방식에는 중요한 한계가 있다.

닉네임만 알면 다른 사람이 해당 회원 이름으로 로그인할 수 있다. 별도의 소유권 확인이 없으므로 회원탈퇴도 타인 사칭 위험을 가진다. 이는 현재 프로젝트가 선택한 닉네임 전용 인증 방식의 한계다.

사용자가 따로 요청하지 않는 한 비밀번호나 추가 인증을 임의로 도입하지 않는다. 대신 이 한계를 새 대화에서 다시 명확히 설명하고 기존 동작을 유지한다.

## 8. 프론트엔드 확인 결과

### 8-1. 기존 프론트엔드 구성

- `index.html`: 게임 설정, 회원가입 및 로그인 폼, 로그아웃·회원탈퇴 버튼, 게임 화면, 결과 화면
- `app.js`: 게임 로직, 타이머, 점수 계산, 회원 상태, API 통신, 순위 표시
- `style.css`: 화면 디자인, 회원 UI, `[hidden]` 처리

HTML은 `style.css`, `app.js`만 연결한다. 확인한 HTML/CSS/JS에는 외부 CDN, 프레임워크, 외부 라이브러리, 외부 URL 참조가 없다.

### 8-2. 회원 UI 요소

`index.html`에서 확인한 요소:

- `#account-status`
- `#register-form`
- `#register-nickname`
- `#login-form`
- `#login-nickname`
- `#logout-button`
- `#withdraw-button`
- `#account-feedback`

`app.js`에서 확인한 함수:

- `updateAccountUI()`
- `refreshAccount()`
- `registerAccount(event)`
- `loginAccount(event)`
- `logoutAccount()`
- `withdrawAccount()`

이벤트 연결:

- 회원가입 폼 submit → `registerAccount`
- 로그인 폼 submit → `loginAccount`
- 로그아웃 버튼 click → `logoutAccount`
- 회원탈퇴 버튼 click → `withdrawAccount`

페이지 최초 실행 시 `updateAccountUI()`, `refreshAccount()`, `updateSetupVisibility()`, `updateRanking()`을 실행한다.

CSS에 `[hidden] { display: none !important; }`가 있으며 회원가입/로그인 폼의 hidden 처리도 확인했다.

### 8-3. API 통신 방식

기존 `app.js`는 상대 경로를 사용한다.

```javascript
fetch('/api/me')
fetch('/api/register', ...)
fetch('/api/login', ...)
fetch('/api/logout', ...)
fetch('/api/account', ...)
fetch('/api/records?...')
```

별도의 API_BASE 변수는 없다. `Authorization: Bearer ...`와 JSON 요청을 사용한다.

이 구조를 유지하려면 프론트엔드와 DRF API가 브라우저 기준으로 동일한 출처(origin)에서 제공되어야 한다.

### 8-4. 프론트엔드 기록

`app.js`에는 다음 키와 함수가 있다.

- `ACCOUNT_TOKEN_KEY = 'numberAdditionAccountTokenV1'`
- `STORAGE_KEY = 'numberAdditionRankingsV1'`
- `getRankings()`
- `getRankingKey()`
- `sortRankings()`

확인한 코드 범위에서는 `getRankings()` 등 로컬 순위 관련 도우미가 실제로 호출되는 위치가 발견되지 않았다. 기존 localStorage 기록을 자동으로 서버로 옮기지 않는다. 마이그레이션이 필요하면 별도 작업으로 명시적으로 진행한다.

DRF 교체 시 `ACCOUNT_TOKEN_KEY`는 바꾸지 않는다. 기존 원본 토큰과 DB의 SHA-256 해시가 유지된다면 현재 브라우저 토큰을 계속 검증할 수 있다.

## 9. 권장 최종 실행 구조

사용자는 Django/DRF가 백엔드 API만 담당하고 프론트엔드에 개입하지 않기를 원한다. 동시에 기존 `app.js`의 상대 경로 API 호출을 유지하고 Cloudflare Tunnel 외부 접속도 하나의 주소로 유지하는 것이 바람직하다.

이를 만족시키는 권장 구조는 Caddy를 정적 파일 서버 겸 역방향 프록시로 두는 방식이다.

```text
브라우저
   |
   | http://127.0.0.1:8080 또는 Cloudflare HTTPS 주소
   v
Caddy :8080
   |-- /, /index.html, /app.js, /style.css
   |       기존 프론트엔드 파일을 변경 없이 제공
   |
   |-- /api/*
           reverse proxy
           |
           v
       Django REST framework :8000
           |
           v
       number_addition.db
```

역할:

- Caddy: 기존 HTML/CSS/JS 정적 파일 제공, `/api/*` 요청을 Django로 전달
- Django + DRF: JSON API, 인증, 데이터베이스 처리만 담당
- SQLite: 기존 DB 파일 유지
- Cloudflare Tunnel: Caddy의 8080 포트로 접속

이 방식의 장점:

- Django 템플릿을 사용하지 않는다.
- Django가 HTML 화면을 생성하지 않는다.
- 프론트엔드 파일은 기존 위치에서 Caddy가 제공한다.
- 기존 `fetch('/api/...')` 상대 경로를 그대로 유지할 수 있다.
- 프론트엔드와 API가 같은 출처로 보이므로 CORS 설정이 필요하지 않다.
- Cloudflare Quick Tunnel 주소 하나만 사용자에게 공유하면 된다.

Caddy는 아직 설치 여부를 확인하지 않았다. 새 대화 첫 단계에서 `caddy version` 또는 `command -v caddy`로 확인한다. 설치되어 있지 않으면 공식 배포 경로를 확인하고 설치 여부를 사용자에게 안내한다.

Caddyfile에서는 프로젝트 루트 전체를 무제한 파일 서버로 노출하지 않는다. 프론트엔드에서 필요한 `/`, `/index.html`, `/app.js`, `/style.css`만 정적 제공 대상으로 제한하고, `/api/*`만 Django로 프록시한다. `.venv`, `.git`, DB 파일, Python 소스, 환경 파일 및 문서가 외부에서 직접 열리지 않도록 한다.

Caddy 공식 문서는 특정 경로만 역방향 프록시로 전달하고 나머지 정적 파일을 제공하는 구성을 지원한다.

## 10. DRF 구현 권장 구조

권장 디렉터리 구조:

```text
숫자더하기/
├── index.html
├── app.js
├── style.css
├── number_addition.db
├── server.py                 # 이전 검증 완료 전까지 보존
├── requirements.txt
├── Caddyfile                 # 새로 구성할 프록시 설정
├── backend/
│   ├── manage.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── asgi.py
│   └── game_api/
│       ├── __init__.py
│       ├── apps.py
│       ├── models.py
│       ├── serializers.py
│       ├── authentication.py
│       ├── permissions.py
│       ├── views.py
│       └── urls.py
└── .venv/
```

구조는 실제 생성 전에 확인하되, 기존 파일을 이동하거나 이름을 변경하지 않는다.

권장 구현:

- `models.py`: 기존 `members`, `records` 테이블을 매핑하는 모델. 기존 테이블은 `managed = False` 사용.
- `serializers.py`: 기존 요청 검증과 camelCase 응답 구조 유지.
- `authentication.py`: `Authorization: Bearer` 토큰을 SHA-256 해시 후 기존 `members.token_hash`와 비교하는 DRF 인증 클래스.
- `permissions.py`: 공개 조회와 회원 전용 저장을 분리할 필요가 있을 때 사용.
- `views.py`: API별 DRF 뷰.
- `urls.py`: 기존 `/api/...` 경로를 그대로 매핑.
- `settings.py`: 기존 DB 파일을 가리키도록 `DATABASES` 설정.

불필요한 Django 기능은 추가하지 않는다.

- Django 템플릿 사용 금지
- Django Admin을 임의로 추가하지 않음
- 기본 User 모델로 기존 회원 데이터 대체 금지
- DRF Browsable API를 기본 렌더러로 사용하지 않음
- SessionAuthentication 또는 BasicAuthentication을 임의로 켜지 않음
- 별도 DB 생성 금지

DRF 렌더러는 JSON 중심으로 제한한다. 에러 응답은 `{"detail": "..."}` 형식을 유지한다.

## 11. 패키지 버전 권장

작성일 기준 공식 자료를 확인한 결과:

- Django 5.2 LTS 최신 패치: 5.2.19
- Django REST framework 최신 릴리스: 3.18.3
- DRF 3.18.x는 Django 5.2, 6.0, 6.1을 지원한다.
- Django 5.2 LTS는 2028년 4월까지 보안 지원이 예정되어 있다.
- 현재 Python 3.12 계열을 사용할 수 있다.

이 프로젝트에는 단기 최신 기능 버전보다 LTS인 Django 5.2 계열을 우선 권장한다.

새 `requirements.txt`의 목표 구성:

```text
Django==5.2.19
djangorestframework==3.18.3
uvicorn>=0.30,<1.0
```

기존 FastAPI는 Django 이전이 완료되고 새 백엔드 검증이 끝날 때까지 제거하지 않는다. `server.py`가 기존 FastAPI에 의존하므로 초기 설치 단계에서 FastAPI를 먼저 제거하면 안 된다.

Django 5.2 공식 지원 정책은 Python 각 마이너 버전의 최신 패치 릴리스를 기준으로 한다. 현재 환경의 Python 3.12.7은 오래된 패치 버전이므로, 초기 호환성 점검에서 문제가 생기면 Python 최신 3.12 패치 업데이트를 별도 검토한다. 사용자 확인 없이 Python이나 가상환경을 교체하지 않는다.

## 12. 단계별 이전 계획

### 1단계. 새 대화 시작 시 환경 재확인

- 현재 프로젝트 경로 확인
- Git 변경사항 재확인
- Caddy 설치 여부 확인
- Python 및 가상환경 확인
- 기존 파일이 이전 대화 이후 바뀌었는지 확인

전체 파일을 다시 출력하지 말고 변경 여부와 필요한 파일만 확인한다.

### 2단계. DB 백업

- FastAPI 서버 종료 여부 확인
- SQLite backup API로 `number_addition.db` 백업
- 백업본의 테이블 수, 회원 수, 기록 수, 무결성 확인
- 원본 DB는 그대로 유지

### 3단계. Django 및 DRF 추가

- 현재 `.venv` 사용
- 기존 Python 버전부터 확인
- Django 5.2 LTS 및 DRF 설치
- 기존 FastAPI는 검증 완료 전까지 유지
- `backend/` 내부에 Django 프로젝트 구성

### 4단계. 기존 DB 연결

- DB 경로를 프로젝트 루트의 `number_addition.db`로 정확히 설정
- 기본 `db.sqlite3` 생성 금지
- 기존 테이블과 컬럼을 모델에 매핑
- 기존 테이블에 대해 스키마 생성·수정 마이그레이션 금지
- WAL, Foreign Key, Busy Timeout 동작 확인

### 5단계. DRF API 구현

아래 순서를 권장한다.

1. `/api/health`
2. 사용자 정의 Bearer 인증
3. `/api/me`
4. `/api/register`
5. `/api/login`
6. `/api/logout`
7. `/api/account`
8. `/api/records` GET
9. `/api/records` POST

각 단계에서 요청/응답 형식과 상태 코드를 검증한다.

### 6단계. 임시 DB로 API 검증

실제 운영 DB를 대상으로 회원가입, 로그인, 로그아웃, 회원탈퇴 테스트를 하지 않는다.

백업본 또는 별도 임시 DB를 대상으로 검증한다.

필수 검사:

- 회원가입
- 중복 닉네임 차단(대소문자 무시)
- 미가입 닉네임 로그인 차단
- 로그인 토큰 발급
- 기존 토큰 무효화
- Bearer 토큰 `/api/me` 확인
- 로그아웃 후 토큰 무효화
- 재로그인
- 기록 저장
- 기록 조회와 TOP 10 정렬
- 비회원 기록 저장 차단
- 회원탈퇴
- 회원탈퇴 후 기록의 `member_id` NULL 및 닉네임 보존
- DB 무결성

### 7단계. Caddy와 기존 프론트엔드 연결

- Caddy 정적 파일 경로를 기존 프로젝트 폴더로 지정
- `/api/*`만 Django로 reverse proxy
- 프론트엔드 경로는 `/`, `/index.html`, `/app.js`, `/style.css`로 제한
- 기존 app.js의 상대 API 경로가 그대로 동작하는지 확인
- 이 단계 전까지 `index.html`, `app.js`, `style.css`는 수정하지 않는 것이 원칙

### 8단계. 로컬 브라우저 검증

예상 접속 주소:

`http://127.0.0.1:8080`

검증:

- 게임 화면 정상 표시
- JavaScript 및 CSS 정상 로드
- 게스트 모드 표시
- 회원가입 및 중복 가입 차단
- 기존 닉네임 로그인
- 회원 닉네임 표시
- 새로고침 후 로그인 유지
- 로그아웃 후 게스트 전환
- 회원탈퇴 후 게스트 전환
- 회원탈퇴 후 기록 보존
- 게스트 기록 조회
- 게스트 기록 저장 차단
- 회원 기록 저장 및 TOP 10 갱신

API 테스트 통과와 브라우저 UI 작동을 별도 결과로 기록한다.

### 9단계. 실행 파일 및 외부 접속 변경

기존 실행 파일은 현재 FastAPI만 실행한다.

현재 `번호판 더하기 실행.bat`:

- Uvicorn `server:app` 실행
- 2초 대기
- `http://127.0.0.1:8000` 열기

이전 후에는 다음 서비스를 연결해야 한다.

- Django ASGI 애플리케이션: `127.0.0.1:8000`
- Caddy: `127.0.0.1:8080`
- 브라우저: `http://127.0.0.1:8080`

Cloudflare Tunnel은 Django 포트가 아니라 Caddy 포트로 전달한다.

기존 터널 명령:

```bash
"/c/Program Files (x86)/cloudflared/cloudflared.exe" tunnel --url http://127.0.0.1:8000
```

이전 후 목표:

```bash
"/c/Program Files (x86)/cloudflared/cloudflared.exe" tunnel --url http://127.0.0.1:8080
```

외부 접속 문서도 새 실행 순서에 맞게 갱신한다.

### 10단계. FastAPI 정리

다음 항목이 모두 검증된 뒤에만 진행한다.

- DRF API 전체 검증
- 브라우저 회원 기능 검증
- 게임 기록 검증
- 외부 PC 접속 검증
- 데이터베이스 보존 검증

그 이후에만 `server.py` 및 FastAPI 의존성을 정리할지 결정한다. 사용자가 요청하지 않은 파일 삭제는 하지 않는다.

## 13. 검증 완료 기준

### API 검증

- 모든 API 경로가 기존 메서드와 동일
- JSON 요청 및 응답 필드 동일
- `Authorization: Bearer` 유지
- `detail` 오류 형식 유지
- 인증 없는 기록 조회 가능
- 인증 없는 기록 저장 불가
- 회원탈퇴 후 기록 보존

### 프론트엔드 검증

- 기존 화면과 게임 로직 변화 없음
- 로그인 UI 정상 표시
- 로그인 후 닉네임 정상 표시
- 로그아웃 및 회원탈퇴 후 게스트 전환
- 새로고침 후 회원 상태 복원
- 기존 API 상대 경로 호출 정상

### 데이터 검증

- 기존 회원 데이터 보존
- 기존 기록 데이터 보존
- `members` 및 `records` 테이블 구조 보존
- 외래 키 `ON DELETE SET NULL` 동작
- 인덱스 보존
- `PRAGMA integrity_check` 결과 `ok`

### 외부 접속 검증

- Cloudflare HTTPS 주소 접속
- 외부 환경에서 게임 화면 표시
- 회원가입 및 로그인
- 기록 저장 및 조회
- 로그아웃 및 회원탈퇴

외부 PC에서 검증하기 전까지 외부 접속 기능을 완료로 판단하지 않는다.

## 14. 기존 게임 기능 보존

기존 게임은 브라우저에서 연산한다. Django/DRF로 게임 연산을 이전하지 않는다.

기존 기능:

- 시간 제한 모드 및 연습 모드
- 게임 시간과 난이도 선택
- 번호판 문제 생성
- 정답 입력 및 판정
- 타이머
- 게임 결과
- 순위표

기존 점수 규칙:

- 정답: +10점
- 오답: -20점
- 문제 제한 시간 초과: -20점

기록 공유 목적:

- 약 20명 규모의 소규모 공유
- 여러 사용자가 하나의 DB 기록과 순위표 공유
- 게스트는 게임 및 기록 조회 가능
- 회원만 기록 저장 가능
- 서버는 사용자가 전송한 점수를 신뢰해 저장
- 점수 조작 방지는 현재 범위에 포함하지 않음

게임 규칙, 난이도, 점수 계산, 화면 디자인을 백엔드 이전 작업과 함께 임의로 변경하지 않는다.

## 15. 실행 및 운영 관련 기존 정보

기존 FastAPI 실행 명령:

```bash
.venv/Scripts/python.exe -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Cloudflare 실행 경로:

```text
C:\Program Files (x86)\cloudflared\cloudflared.exe
```

버전 확인 당시 `2026.10.7`.

기존 Quick Tunnel은 실행할 때마다 주소가 바뀔 수 있다. 서버 PC가 종료되거나 서버/프록시/터널 프로세스가 종료되면 외부 접속이 중단된다.

최종 운영에는 Django, Caddy, Cloudflare Tunnel 세 프로세스가 필요하다. 실행 배치 파일로 묶을 수 있지만 각 프로세스가 정상 실행되었는지 개별 확인 가능해야 한다.

## 16. 파일 관리 및 작업 방식

- Git Bash 사용
- 가상환경은 기존 `.venv` 사용
- 파일 편집기를 열도록 요구하지 않음
- 코드 확인 및 수정을 터미널 명령어로 진행
- 한 번에 하나의 단계만 진행
- 먼저 관련 코드 위치를 찾고 필요한 부분만 출력
- 존재하지 않는 파일이나 함수를 가정하지 않음
- 수정 전 기존 내용과 일치하는지 검사
- Python으로 파일 변경 시 예상 문자열이 다르면 중단
- 여러 파일 수정은 가능한 한 하나의 안전한 스크립트로 진행
- 실제 브라우저 검증 전 UI 완료 판정 금지
- 데이터베이스 삭제, 초기화, 강제 재생성 금지
- 새 라이브러리나 서버 프로그램이 필요하면 필요성을 먼저 설명
- 사용자가 완료 결과를 보내면 다음 한 단계 진행

현재 `.gitignore`:

```text
.venv/
__pycache__/
*.py[cod]
number_addition.db
number_addition.db-shm
number_addition.db-wal
.env
```

Django 구성 후 `backend/__pycache__/` 등 캐시가 Git에 포함되지 않는지 확인한다. 새 SQLite DB가 생성되지 않도록 특히 주의한다.

## 17. 아직 확인되지 않은 사항

다음 항목은 새 대화에서 필요할 때 확인한다.

- Caddy가 이미 설치되어 있는지
- 새 Django 구조가 실제로 생성되어 있는지(현재는 미생성)
- DRF 설치 여부(현재 미설치)
- 새 Django 설정에서 기존 DB 연결 경로가 정확한지
- Caddy reverse proxy가 실제로 `/api/*`만 Django로 전달하는지
- 브라우저에서 로그인/로그아웃/회원탈퇴가 실제 작동하는지
- 새 구조에서 다른 PC의 외부 접속이 성공하는지

기존 FastAPI API는 임시 DB를 대상으로 한 테스트가 통과했지만, 사용자는 실제 화면의 로그인·로그아웃·회원탈퇴가 정상 작동하지 않는다고 보고했다. 이번 DRF 이전은 코드 이식만으로 완료 처리하지 말고 브라우저까지 검증해야 한다.

## 18. 새 대화의 첫 작업

새 대화에서는 설명을 길게 반복하지 말고, 이 문서를 읽은 상태를 전제로 아래 확인부터 시작한다.

1. 프로젝트 경로와 Git 변경사항을 확인한다.
2. Caddy 설치 여부를 확인한다.
3. 기존 `.venv`의 Python 버전을 확인한다.
4. DB 백업 절차를 준비한다.
5. DB를 보존하는 Django/DRF 구성부터 시작한다.

첫 명령은 Caddy 설치 여부와 현재 작업 트리 상태를 확인하는 최소 범위로 제시한다. 바로 기존 파일을 변경하거나 패키지를 설치하지 않는다.

이전 작업은 한 번에 한 단계씩 진행한다. 사용자가 결과를 전달하기 전 다음 단계로 넘어가지 않는다.

---

## 19. 공식 참고 자료

버전과 지원 기간은 작성일 기준으로 확인했다. 새 대화에서 실제 설치 직전 공식 문서를 다시 확인한다.

- Django 다운로드 및 지원 버전: https://www.djangoproject.com/download/
- Django 5.2 릴리스 문서: https://docs.djangoproject.com/en/5.2/releases/5.2/
- Django REST framework 릴리스 기록: https://www.django-rest-framework.org/community/release-notes/
- Django REST framework 공식 문서: https://www.django-rest-framework.org/
- Caddy 정적 파일과 역방향 프록시 구성: https://caddyserver.com/docs/quick-starts/reverse-proxy
- Caddy 설치: https://caddyserver.com/docs/install

