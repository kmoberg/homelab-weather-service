from fastapi import FastAPI
from src.routes import weather, energy

app = FastAPI(
    title="Weather & Energy API",
    description="API to access METAR, forecast, and Netatmo data",
    version="0.5.0"
)

app.include_router(weather.router, prefix="/api/weather", tags=["weather"])