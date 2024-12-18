from src.utils.logging_config import logger
import requests

def fetch_faa_metar(stations):
    # If stations is a list, join them by commas
    if isinstance(stations, list):
        station_str = ",".join(stations)
    else:
        station_str = stations

    url = f"https://aviationweather.gov/api/data/metar?ids={station_str}&format=json"
    logger.debug(f"Fetching METAR data from {url}")
    response = requests.get(url)
    try:
        response.raise_for_status()
    except requests.HTTPError as err:
        logger.error(f"HTTP error while fetching METAR data: {err}")
        return []

    data = response.json()
    if not data:
        logger.debug("No METAR data returned by the API")
        return []

    logger.debug(f"Received METAR data for {len(data)} stations")



    # If there’s no data or it's empty, return empty list
    if not data:
        return []

    metars = []
    for item in data:
        def to_float(val):
            try:
                return float(val)
            except:
                return None

        # Convert altimeter from hPa to inHg if desired
        altim_hpa = item.get("altim")
        altim_in_hg = (to_float(altim_hpa) * 0.02953) if altim_hpa is not None else None

        # Handle visibility
        visib_raw = item.get("visib")
        visib_str = str(visib_raw) if visib_raw is not None else None
        if visib_str == "9999":
            # 9999 typically means >=10km (~6.2 miles)
            visibility_statute_mi = 6.2
        elif visib_str and visib_str.endswith('+'):
            base_val = visib_str.rstrip('+')
            visibility_statute_mi = to_float(base_val)
        else:
            visibility_statute_mi = to_float(visib_str)

        metars.append({
            "station_id": item.get("icaoId"),
            "observation_time": item.get("reportTime"),
            "temp_c": to_float(item.get("temp")),
            "dewpoint_c": to_float(item.get("dewp")),
            "wind_dir_deg": to_float(item.get("wdir")),
            "wind_speed_kt": to_float(item.get("wspd")),
            "altim_hpa": to_float(altim_hpa),
            "altim_in_hg": altim_in_hg,
            "visibility_statute_mi": visibility_statute_mi,
            "wx_string": item.get("rawOb", "")
        })

    return metars