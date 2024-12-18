import requests
import os
from src.utils.logging_config import logger

YR_LATITUDE = os.getenv("YR_LATITUDE", "58.9959")
YR_LONGITUDE = os.getenv("YR_LONGITUDE", "5.6799")
YR_USER_AGENT = os.getenv("YR_USER_AGENT", "MyWeatherApp/1.0 https://github.com/kmoberg")

def fetch_yr_forecast(lat=YR_LATITUDE, lon=YR_LONGITUDE):
    """
    Fetch forecast data from yr.no for the given latitude and longitude.
    Returns a dictionary with current conditions and short-term forecast data.
    Also returns a list of future forecasts.
    """
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}"
    headers = {
        "User-Agent": YR_USER_AGENT
    }

    logger.debug(f"Fetching forecast data from yr.no: {url}")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error fetching yr.no forecast: {e}")
        return None

    data = response.json()

    timeseries = data.get("properties", {}).get("timeseries", [])
    if not timeseries:
        logger.debug("No forecast timeseries data returned by yr.no.")
        return None

    # Current conditions: first timeseries entry
    current_entry = timeseries[0]
    current_time = current_entry.get("time")
    current_data = current_entry.get("data", {})
    instant_details = current_data.get("instant", {}).get("details", {})

    current_temp = instant_details.get("air_temperature")
    current_wind_speed = instant_details.get("wind_speed")
    current_cloud_fraction = instant_details.get("cloud_area_fraction")
    current_pressure = instant_details.get("air_pressure_at_sea_level")
    current_humidity = instant_details.get("relative_humidity")

    # Precipitation forecasts
    precip_1h = None
    precip_6h = None
    precip_12h = None

    next_1_hours = current_data.get("next_1_hours", {})
    if "details" in next_1_hours:
        precip_1h = next_1_hours["details"].get("precipitation_amount")

    next_6_hours = current_data.get("next_6_hours", {})
    if "details" in next_6_hours:
        precip_6h = next_6_hours["details"].get("precipitation_amount")

    next_12_hours = current_data.get("next_12_hours", {})
    if "details" in next_12_hours:
        precip_12h = next_12_hours["details"].get("precipitation_amount")

    # Construct a forecast dictionary for the current conditions
    current_forecast = {
        "observation_time": current_time,
        "temp_c": current_temp,
        "wind_speed_m_s": current_wind_speed,
        "cloud_fraction_percent": current_cloud_fraction,
        "pressure_hpa": current_pressure,
        "relative_humidity_percent": current_humidity,
        "precip_1h_mm": precip_1h,
        "precip_6h_mm": precip_6h,
        "precip_12h_mm": precip_12h
    }

    # If you want to store multiple future forecasts, you can parse more entries.
    # For example, get the next 5 forecast entries (each hourly):
    future_forecasts = []
    for entry in timeseries[1:6]:  # next 5 hours
        t = entry.get("time")
        d = entry.get("data", {})
        i = d.get("instant", {}).get("details", {})

        future_forecasts.append({
            "time": t,
            "temp_c": i.get("air_temperature"),
            "wind_speed_m_s": i.get("wind_speed"),
            "cloud_fraction_percent": i.get("cloud_area_fraction"),
            "pressure_hpa": i.get("air_pressure_at_sea_level"),
            "relative_humidity_percent": i.get("relative_humidity"),
            "precip_1h_mm": d.get("next_1_hours", {}).get("details", {}).get("precipitation_amount")
        })

    logger.info(
        f"Fetched yr.no forecast at {current_time}: temp={current_temp}C, wind={current_wind_speed}m/s, "
        f"precip_1h={precip_1h}mm"
    )

    return {
        "current_forecast": current_forecast,
        "future_forecasts": future_forecasts
    }