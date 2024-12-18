from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from src.utils.config import Config

def get_influx_client():
    return InfluxDBClient(
        url=f"http://{Config.INFLUX_HOST}:8086",
        token=Config.INFLUX_TOKEN,
        org=Config.INFLUX_ORG
    )

def write_measurement(measurement_name: str, fields: dict, tags: dict = None, timestamp=None):
    with get_influx_client() as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        p = Point(measurement_name)
        if tags:
            for k, v in tags.items():
                p = p.tag(k, v)
        for k, v in fields.items():
            p = p.field(k, v)
        if timestamp:
            p = p.time(timestamp)  # Set the timestamp explicitly
        write_api.write(bucket=Config.INFLUX_BUCKET, record=p)