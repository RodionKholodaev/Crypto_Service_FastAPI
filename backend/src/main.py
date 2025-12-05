from fastapi import FastAPI

app = FastAPI(
    title="Trading Bot Manager API",
    description="API для управления криптовалютными торговыми ботами",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {
        "message": "Trading Bot Manager API is running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
