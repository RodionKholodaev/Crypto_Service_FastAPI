"""
Главный файл FastAPI приложения
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth

app = FastAPI(
    title="Trading Bot Manager API",
    description="API для управления криптовалютными торговыми ботами",
    version="1.0.0"
)

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth.router)


@app.get("/")
async def root():
    """Главная страница API"""
    return {
        "message": "Trading Bot Manager API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth",
            "docs": "/docs",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса"""
    return {
        "status": "ok",
        "service": "backend"
    }
