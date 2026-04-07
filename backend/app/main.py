from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes, stations, status

app = FastAPI(
    title="건강길찾기 API (Health Directions)",
    description="버스·따릉이·신호등 실시간 데이터 기반 경로 추천",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router, prefix="/api")
app.include_router(stations.router, prefix="/api")
app.include_router(status.router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}
