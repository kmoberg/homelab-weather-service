import datetime
import requests
from src.database.influx_client import write_measurement
from src.utils.logging_config import logger

def fetch_energy_prices():
    """
    Fetches energy prices for today and tomorrow if needed. Prices only update once daily.
    For tomorrow, check after 1 PM local time (Norwegian time).
    """
    # Get current time and local Norwegian time
    now = datetime.datetime.now()
    local_time = now + datetime.timedelta(hours=1)  # Assuming UTC + 1 for Norway

    # Fetch today's prices
    today_url = create_energy_price_url(local_time)
    prices_today = fetch_day_prices(today_url)
    if prices_today:
        store_energy_prices(prices_today)

    # Fetch tomorrow's prices after 1 PM
    if local_time.hour >= 13:
        tomorrow_url = create_energy_price_url(local_time + datetime.timedelta(days=1))
        prices_tomorrow = fetch_day_prices(tomorrow_url)
        if prices_tomorrow:
            store_energy_prices(prices_tomorrow)

def create_energy_price_url(date):
    """
    Create the API URL for the given date.
    """
    year = date.strftime("%Y")
    month_day = date.strftime("%m-%d")
    return f"https://www.hvakosterstrommen.no/api/v1/prices/{year}/{month_day}_NO2.json"

def fetch_day_prices(url):
    """
    Fetch energy prices for a given day from the API.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        logger.info(f"Fetched energy prices from {url}")
        return response.json()  # Assuming the API returns a JSON response
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch energy prices from {url}: {e}")
        return []


def store_energy_prices(prices):
    """
    Store each hour's price data in InfluxDB as NOK/øre per kWh.
    """
    for entry in prices:
        # Parse the start time of the hourly period
        dt = datetime.datetime.fromisoformat(entry["time_start"])

        # Fetch the price in NOK (if available)
        nok_per_kwh = entry.get("NOK_per_kWh")
        if nok_per_kwh is None:
            logger.warning(f"Missing NOK price for time {entry['time_start']}. Skipping...")
            continue

        # Convert NOK to øre
        price_in_ore = round(nok_per_kwh * 100)

        # Prepare the data point
        fields = {"price_per_kwh_ore": price_in_ore}  # Store price in øre
        tags = {"region": "NO2", "currency": "NOK"}

        # Write to InfluxDB with the specific timestamp
        write_measurement("energy_prices", fields, tags, timestamp=dt)

    logger.info("Wrote hourly energy prices to InfluxDB")