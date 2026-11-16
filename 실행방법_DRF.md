# 번호판 더하기 실행 방법 (Django + DRF + Caddy)

기준일: 2026-11-16

## 1. 실행 구조

```text
브라우저 (로컬 http://127.0.0.1:8080 또는 외부 https://*.trycloudflare.com)
   |
   v
Caddy (:8080, bind 127.0.0.1)
   ├── /, /index.html, /app.js, /style.css  ──> 정적 파일 제공
   ├── /api/*                               ──> reverse_proxy 127.0.0.1:8000 (Django + DRF)
   └── 그 외 모든 경로(.db, .py, .git 등)    ──> 404 차단
```

- **백엔드 API**: Django 5.2.19 + Django REST framework 3.18.3 (Uvicorn ASGI, `127.0.0.1:8000`)
- **프록시/정적 파일**: Caddy 2.11.9 (`127.0.0.1:8080`)
- **외부 접속**: Cloudflare Quick Tunnel → `http://127.0.0.1:8080`
- **데이터베이스**: 프로젝트 루트 `number_addition.db`

---

## 2. 사전 확인

- 프로젝트 경로: `/c/Users/SSAFY/Desktop/minjun/밍듀니/my/숫자더하기`
- Python 가상환경: `.venv` (Django, djangorestframework, uvicorn 설치 완료)
- Caddy: `winget install -e --id CaddyServer.Caddy` 로 설치 완료
- Cloudflared: `"/c/Program Files (x86)/cloudflared/cloudflared.exe"`

---

## 3. 로컬 실행 (Git Bash 터미널 2개)

### 터미널 1: Django ASGI 서버 (:8000)

```bash
cd "/c/Users/SSAFY/Desktop/minjun/밍듀니/my/숫자더하기" && \
.venv/Scripts/python.exe -m uvicorn config.asgi:application --app-dir backend --host 127.0.0.1 --port 8000
```

### 터미널 2: Caddy 정적 파일 + 역방향 프록시 (:8080)

```bash
cd "/c/Users/SSAFY/Desktop/minjun/밍듀니/my/숫자더하기" && \
CADDY_BIN="$(command -v caddy 2>/dev/null || find "$LOCALAPPDATA/Microsoft/WinGet/Packages" -maxdepth 3 -name caddy.exe 2>/dev/null | head -n 1)" && \
"$CADDY_BIN" run --config Caddyfile --adapter caddyfile
```

### 로컬 접속 주소

- 게임 화면: `http://127.0.0.1:8080`
- API 상태 확인: `http://127.0.0.1:8080/api/health` (`{"status":"ok"}`)

---

## 4. 외부 접속 실행 (터미널 3 추가)

터미널 1(Django)과 터미널 2(Caddy)가 실행 중인 상태에서 세 번째 Git Bash 터미널을 열고 실행합니다.

```bash
"/c/Program Files (x86)/cloudflared/cloudflared.exe" tunnel --url http://127.0.0.1:8080
```

출력되는 `https://임의의문자열.trycloudflare.com` 주소를 외부 사용자에게 전달합니다.  
(`ALLOWED_HOSTS`에 `.trycloudflare.com`이 포함되어 있어 별도 설정 없이 동작합니다.)

---

## 5. 종료 및 주의사항

- 종료 순서: 각 터미널에서 `Ctrl + C` (Cloudflare Tunnel → Caddy → Django ASGI)
- **주의**:
  - 기존 `server.py` (`uvicorn server:app`)는 더 이상 실행하지 않습니다.
  - `number_addition.db`에 대해 `manage.py migrate`나 `flush`를 실행하지 않습니다.
  - `Caddyfile`은 `127.0.0.1:8080`만 바인딩하며 `/`, `/index.html`, `/app.js`, `/style.css`, `/api/*` 외 경로는 404로 차단합니다.
