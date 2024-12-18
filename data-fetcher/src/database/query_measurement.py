from influxdb_client import Point
from influxdb_client.client.query_api import QueryApi
from src.utils.logging_config import logger
from src.utils.config import Config


def query_measurement(query):
    """
    Query InfluxDB and return the results.
    """
    try:
        query_api = Config.INFLUX_CLIENT.query_api()
        results = query_api.query(query)
        # Extract records from the query result
        if results:
            return [record.values for table in results for record in table.records]
        return []
    except Exception as e:
        logger.error(f"Failed to query InfluxDB: {e}", exc_info=True)
        return []