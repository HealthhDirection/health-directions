# Health Directions 팀 세팅 가이드

## 1) 필수 설치
- Git
- Node.js 20 LTS + npm
- Python 3.11 권장
- PostgreSQL
- Docker Desktop (Redis 실행용)

## 2) 프로젝트 받기
```powershell
git clone https://github.com/HealthhDirection/health-directions.git
cd health-directions
```

## 3) 환경변수 설정
루트 디렉터리(`health-directions`)에서:

```powershell
Copy-Item .env.example .env
```

`.env`에서 최소 아래 값은 본인 환경에 맞게 수정:
- `PG_DSN` (PostgreSQL 접속 정보)
- `REDIS_URL`

선택(기능 확장용) API 키:
- `BUS_API_KEY`
- `BIKE_API_KEY`
- `SIGNAL_API_KEY`
- `TMAP_APP_KEY`
- `VITE_KAKAO_MAP_KEY`

## 4) Redis 실행
루트 디렉터리에서:

```powershell
docker compose up -d redis
```

## 5) PostgreSQL 준비
- PostgreSQL 실행
- DB 생성: `gangseo_transit`
- 기본 예시(`.env.example` 기준): `localhost:5433`

예시(SQL):
```sql
CREATE DATABASE gangseo_transit;
```

## 6) 백엔드 설치 및 실행
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app/db/init.py
uvicorn app.main:app --reload --port 8000
```

## 7) 프론트엔드 설치 및 실행
새 터미널에서:

```powershell
cd frontend
npm install
npm run dev
```

## 8) 접속 주소
- 프론트엔드: `http://localhost:5173`
- 백엔드: `http://localhost:8000`
- 헬스체크: `http://localhost:8000/health`

## 9) 자주 발생하는 문제
- `git push -u origin main`에서 `src refspec main does not match any`:
  - 초기 커밋이 없을 때 발생
  - 아래 순서로 해결

```powershell
git add .
git commit -m "Initial commit"
git push -u origin main
```
