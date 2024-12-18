import os

class Config:
    INFLUX_HOST = os.getenv("INFLUX_HOST", "influxdb")
    INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "weather")
    INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "your_influx_token")
    INFLUX_ORG = os.getenv("INFLUX_ORG", "myorg")
    FAA_API_KEY = os.getenv("FAA_API_KEY", "")