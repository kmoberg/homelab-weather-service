import requests
import os
from src.utils.logging_config import logger
from datetime import datetime

NETATMO_CLIENT_ID = os.getenv("NETATMO_CLIENT_ID")
NETATMO_CLIENT_SECRET = os.getenv("NETATMO_CLIENT_SECRET")
NETATMO_USERNAME = os.getenv("NETATMO_USERNAME")
NETATMO_PASSWORD = os.getenv("NETATMO_PASSWORD")

TOKEN_URL = "https://api.netatmo.com/oauth2/token"
STATIONS_DATA_URL = "https://api.netatmo.com/api/getstationsdata"

import requests
import os
from src.utils.logging_config import logger

NETATMO_CLIENT_ID = os.getenv("NETATMO_CLIENT_ID")
NETATMO_CLIENT_SECRET = os.getenv("NETATMO_CLIENT_SECRET")
NETATMO_ACCESS_TOKEN = os.getenv("NETATMO_ACCESS_TOKEN")
NETATMO_REFRESH_TOKEN = os.getenv("NETATMO_REFRESH_TOKEN")

TOKEN_URL = "https://api.netatmo.com/oauth2/token"


class NetatmoAuthError(Exception):
    pass


def refresh_netatmo_token():
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": NETATMO_REFRESH_TOKEN,
        "client_id": NETATMO_CLIENT_ID,
        "client_secret": NETATMO_CLIENT_SECRET
    }

    response = requests.post(TOKEN_URL, data=payload)
    if response.status_code != 200:
        raise NetatmoAuthError(f"Failed to refresh token: {response.text}")

    data = response.json()
    new_access_token = data["access_token"]
    new_refresh_token = data["refresh_token"]

    # Update environment variables or write them to a secure store
    # If you can't write to .env automatically, you might just store them in memory.
    # For a long-term solution, consider writing the updated tokens to a file or key store.

    logger.info("Netatmo access token refreshed successfully")
    return new_access_token, new_refresh_token


def get_netatmo_token():
    # If we trust the existing access token is valid until it expires, we can just return it.
    # If we want to always refresh for demonstration, call refresh_netatmo_token().
    # In reality, you should check if the token is expired or near expiration before refreshing.

    new_access_token, new_refresh_token = refresh_netatmo_token()
    # Update your global variables or however you store tokens
    # In a real scenario, you might rewrite .env file or use another storage method
    # For simplicity, we’ll just overwrite the global variables here
    global NETATMO_ACCESS_TOKEN, NETATMO_REFRESH_TOKEN
    NETATMO_ACCESS_TOKEN = new_access_token
    NETATMO_REFRESH_TOKEN = new_refresh_token
    return NETATMO_ACCESS_TOKEN


def fetch_netatmo_data():
    token = get_netatmo_token()
    headers = {
        "Authorization": f"Bearer {token}"
    }
    params = {
        "get_favorites": "false"
    }

    response = requests.get("https://api.netatmo.com/api/getstationsdata", headers=headers, params=params)
    response.raise_for_status()
    data = response.json()

    devices = data.get("body", {}).get("devices", [])
    if not devices:
        logger.warning("No Netatmo devices found")
        return None

    main_station = devices[0]
    station_name = main_station.get("station_name", "Unknown Station")
    dash_data = main_station.get("dashboard_data", {})

    temperature = dash_data.get("Temperature")
    humidity = dash_data.get("Humidity")
    pressure = dash_data.get("Pressure", None)
    rain = dash_data.get("Rain", 0.0)
    wind_strength = dash_data.get("WindStrength", None)
    wind_angle = dash_data.get("WindAngle", None)

    return {
        "station_name": station_name,
        "temperature": temperature,
        "humidity": humidity,
        "pressure_hpa": pressure,
        "rain_mm": rain,
        "wind_strength_kmh": wind_strength,
        "wind_angle_deg": wind_angle,
        "time_utc": dash_data.get("time_utc")
    }


def update_env_tokens(new_access, new_refresh):
    lines = []
    with open(".env", "r") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.startswith("NETATMO_ACCESS_TOKEN="):
            new_lines.append(f"NETATMO_ACCESS_TOKEN={new_access}\n")
        elif line.startswith("NETATMO_REFRESH_TOKEN="):
            new_lines.append(f"NETATMO_REFRESH_TOKEN={new_refresh}\n")
        else:
            new_lines.append(line)

    with open(".env", "w") as f:
        f.writelines(new_lines)
