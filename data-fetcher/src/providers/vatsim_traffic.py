"""
providers/vatsim_traffic.py

This module fetches VATSIM traffic data and stores it in InfluxDB.
It does NOT modify existing config.py or influx_client.py.
"""

import logging
import time
from collections import Counter

import requests

# Import your existing config and influx client
from src.utils import config
from src.database.influx_client import influx_client  # or get_influx_client

def fetch_and_store_vatsim_traffic(measurement_name: str = "vatsim_stats") -> None:
    """
    High-level function to fetch VATSIM traffic data and store it in InfluxDB.

    Args:
        measurement_name (str): The name of the measurement in InfluxDB.
    """
    try:
        # 1. Fetch the data
        data = _fetch_vatsim_data()

        # 2. Parse the data
        stats = _parse_vatsim_data(data)

        # 3. Write to InfluxDB
        _store_to_influx(stats, measurement_name)

        logging.info("[vatsim_traffic] Successfully stored VATSIM traffic stats.")
    except Exception as exc:
        logging.error(f"[vatsim_traffic] Error fetching/storing VATSIM traffic data: {exc}")


def _fetch_vatsim_data() -> dict:
    """
    Fetch the VATSIM data feed using exponential backoff,
    leveraging configuration from config.py (if available).

    Returns:
        dict: Parsed JSON from VATSIM data feed.
    """
    # Example references to config variables; adjust to your real keys:
    url = config.VATSIM_DATAFEED_URL  # e.g. "https://data.vatsim.net/v3/vatsim-data.json"
    max_retries = getattr(config, "VATSIM_MAX_RETRIES", 5)
    initial_backoff = getattr(config, "VATSIM_INITIAL_BACKOFF", 5)

    backoff = initial_backoff
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data

        except (requests.exceptions.RequestException, ValueError) as err:
            logging.warning(
                f"[vatsim_traffic] Attempt {attempt+1}/{max_retries} failed: {err}"
            )
            if attempt == max_retries - 1:
                # Re-raise if we're on the last attempt
                raise
            time.sleep(backoff)
            backoff *= 2

    # Should never reach here because we raise on the last attempt.
    raise RuntimeError("[vatsim_traffic] Failed to fetch VATSIM data after max retries.")


def _parse_vatsim_data(data: dict) -> dict:
    """
    Parse raw VATSIM JSON data to extract relevant statistics.

    Returns:
        dict: {
            "total_clients": int,
            "pilot_count": int,
            "controller_count": int,
            "atis_count": int,
            "supervisor_count": int,
            "most_popular_ac": str,
            "most_popular_dep": str,
            "most_popular_arr": str
        }
    """
    pilots = data.get("pilots", [])
    controllers = data.get("controllers", [])
    atis = data.get("atis", [])

    pilot_count = len(pilots)
    controller_count = len(controllers)
    atis_count = len(atis)
    total_clients = pilot_count + controller_count + atis_count

    # Supervisors/Administrators typically rating >= 7
    supervisor_count = 0
    for ctrl in controllers:
        if ctrl.get("rating", 0) >= 7:
            supervisor_count += 1
    for a in atis:
        if a.get("rating", 0) >= 7:
            supervisor_count += 1

    # Identify most popular aircraft/dep/arr among pilots
    ac_counter = Counter()
    dep_counter = Counter()
    arr_counter = Counter()

    for pilot in pilots:
        fp = pilot.get("flight_plan", {})
        ac = fp.get("aircraft", "Unknown")
        dep = fp.get("departure", "Unknown")
        arr = fp.get("arrival", "Unknown")

        ac_counter[ac] += 1
        dep_counter[dep] += 1
        arr_counter[arr] += 1

    most_popular_ac = ac_counter.most_common(1)[0][0] if ac_counter else "N/A"
    most_popular_dep = dep_counter.most_common(1)[0][0] if dep_counter else "N/A"
    most_popular_arr = arr_counter.most_common(1)[0][0] if arr_counter else "N/A"

    return {
        "total_clients": total_clients,
        "pilot_count": pilot_count,
        "controller_count": controller_count,
        "atis_count": atis_count,
        "supervisor_count": supervisor_count,
        "most_popular_ac": most_popular_ac,
        "most_popular_dep": most_popular_dep,
        "most_popular_arr": most_popular_arr,
    }


def _store_to_influx(stats: dict, measurement: str):
    """
    Write the parsed statistics to InfluxDB using the existing influx_client.

    Args:
        stats (dict): The dictionary of parsed VATSIM stats.
        measurement (str): The Influx measurement to store data in.
    """

    # If your existing client is a global variable 'influx_client', just use it directly
    # Otherwise, if you have get_influx_client() or something, call that instead.
    # e.g. client = get_influx_client()

    json_body = [
        {
            "measurement": measurement,
            "fields": {
                "total_clients": stats["total_clients"],
                "pilot_count": stats["pilot_count"],
                "controller_count": stats["controller_count"],
                "atis_count": stats["atis_count"],
                "supervisor_count": stats["supervisor_count"],
            },
            # Store these as tags if you want to query/filter on them
            "tags": {
                "most_popular_ac": stats["most_popular_ac"],
                "most_popular_dep": stats["most_popular_dep"],
                "most_popular_arr": stats["most_popular_arr"],
            },
        }
    ]

    influx_client.write_points(json_body)