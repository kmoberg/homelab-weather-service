from influxdb_client import InfluxDBClient
from src.utils.config import Config

def get_influx_client():
    return InfluxDBClient(
        url=f"http://{Config.INFLUX_HOST}:8086",
        token=Config.INFLUX_TOKEN,
        org=Config.INFLUX_ORG
    )

def query_influx(flux_query: str):
    with get_influx_client() as client:
        query_api = client.query_api()
        return list(query_api.query(org=Config.INFLUX_ORG, query=flux_query))