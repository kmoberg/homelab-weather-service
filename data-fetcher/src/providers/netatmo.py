import os
import json
from datetime import datetime
from src.utils.logging_config import logger

TOKEN_FILE = "/app/tokens/netatmo_tokens.json"

NETATMO_CLIENT_ID = os.getenv("NETATMO_CLIENT_ID")
NETATMO_CLIENT_SECRET = os.getenv("NETATMO_CLIENT_SECRET")
NETATMO_USERNAME = os.getenv("NETATMO_USERNAME")
NETATMO_PASSWORD = os.getenv("NETATMO_PASSWORD")

# You might choose to not use the env tokens at all and rely solely on the file.
initial_access_token = os.getenv("NETATMO_ACCESS_TOKEN", "")
initial_refresh_token = os.getenv("NETATMO_REFRESH_TOKEN", "")

class NetatmoAuthError(Exception):
    pass

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
            return data.get("access_token"), data.get("refresh_token")
    # If file doesn't exist, use initial tokens from env or return None
    if initial_access_token and initial_refresh_token:
        return initial_access_token, initial_refresh_token
    return None, None

def save_tokens(access_token, refresh_token):
    with open(TOKEN_FILE, "w") as f:
        json.dump({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "updated_at": datetime.utcnow().isoformat()
        }, f)
    logger.info("Netatmo tokens saved to file")

def refresh_netatmo_token():
    import requests
    access_token, refresh_token = load_tokens()
    if not refresh_token:
        raise NetatmoAuthError("No refresh token available")

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": NETATMO_CLIENT_ID,
        "client_secret": NETATMO_CLIENT_SECRET
    }

    response = requests.post("https://api.netatmo.com/oauth2/token", data=payload)
    if response.status_code != 200:
        raise NetatmoAuthError(f"Failed to refresh token: {response.text}")

    data = response.json()
    new_access_token = data["access_token"]
    new_refresh_token = data["refresh_token"]
    save_tokens(new_access_token, new_refresh_token)
    logger.info("Netatmo access token refreshed successfully")
    return new_access_token, new_refresh_token

def get_netatmo_token():
    # Try to use current tokens
    access_token, refresh_token = load_tokens()
    # If no tokens at all, you might need to do an initial login flow (not shown here)
    # or just trust that we already have valid tokens.
    # If token is expired or you prefer to always refresh:
    # For simplicity, always refresh here:
    new_access_token, new_refresh_token = refresh_netatmo_token()
    return new_access_token

def fetch_netatmo_data():
    import requests
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