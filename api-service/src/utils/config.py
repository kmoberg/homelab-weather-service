import os

class Config:
    INFLUX_HOST = os.getenv("INFLUX_HOST", "influxdb")
    INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "weather")
    INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
    INFLUX_ORG = os.getenv("INFLUX_ORG", "myorg")