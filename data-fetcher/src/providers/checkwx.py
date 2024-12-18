import requests
from src.utils.logging_config import logger
import os

CHECKWX_API_KEY = os.getenv("CHECKWX_API_KEY", "")


def fetch_checkwx_metar(stations):
    """
    Fetches METAR data from CheckWX for one or multiple stations.
    If multiple stations are provided in a list, they are fetched in a single request by
    joining them with commas.
    """
    if isinstance(stations, list):
        station_str = ",".join(stations)
    else:
        station_str = stations

    url = f"https://api.checkwx.com/metar/{station_str}/decoded"
    headers = {"X-API-Key": CHECKWX_API_KEY}
    logger.debug(f"Fetching METAR data from CheckWX: {url}")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error fetching CheckWX METAR: {e}")
        return []

    # Parse the response
    data = response.json().get("data", [])
    if not data:
        logger.debug("No METAR data returned by CheckWX.")
        return []

    logger.debug(f"Received METAR data for {len(data)} station(s) from CheckWX")

    # Helper for safe float conversion
    def to_float(val):
        try:
            return float(val)
        except:
            return None

    metars = []
    for item in data:
        raw_text = item.get("raw_text", "")
        icao = item.get("icao")
        observed = item.get("observed")  # ISO 8601 datetime string
        temp_c = to_float(item.get("temperature", {}).get("celsius"))
        dew_c = to_float(item.get("dewpoint", {}).get("celsius"))
        wind_dir = to_float(item.get("wind", {}).get("degrees"))
        wind_spd = to_float(item.get("wind", {}).get("speed_kts"))

        # Barometer can be taken directly in hPa or inHg
        altim_hpa = to_float(item.get("barometer", {}).get("hpa"))
        altim_in_hg = to_float(item.get("barometer", {}).get("hg"))

        # Visibility can be read from miles_float
        visibility_mi = to_float(item.get("visibility", {}).get("miles_float"))

        # Append to the results
        metars.append({
            "station_id": icao,
            "observation_time": observed,
            "temp_c": temp_c,
            "dewpoint_c": dew_c,
            "wind_dir_deg": wind_dir,
            "wind_speed_kt": wind_spd,
            "altim_hpa": altim_hpa,
            "altim_in_hg": altim_in_hg,
            "visibility_statute_mi": visibility_mi,
            "wx_string": raw_text
        })

    return metars