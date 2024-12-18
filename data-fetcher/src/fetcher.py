from src.providers.faa import fetch_faa_metar
from src.providers.checkwx import fetch_checkwx_metar
from src.providers.vatsim import fetch_vatsim_metar
from src.providers.yrno import fetch_yr_forecast
from src.providers.netatmo import fetch_netatmo_data
from src.providers.energy import fetch_energy_prices
from src.database.influx_client import write_measurement
from src.utils.logging_config import logger
import time


def get_airport_metars_from_providers(stations):
    """
    Attempt to retrieve METAR data from multiple sources in order:
    1. FAA
    2. CheckWX
    3. VATSIM

    Returns a dictionary of weather infomration keyed by station_id, with the chosen METAR
    data as the value. If no data is available, the value is None.
    """

    # FAA
    try:
        faa_metars = fetch_faa_metar(stations)
    except Exception as e:
        logger.error(f"Error fetching METAR data from FAA: {e}")
        faa_metars = []

    # CheckWX
    try:
        checkwx_metars = fetch_checkwx_metar(stations)
    except Exception as e:
        logger.error(f"Error fetching METAR data from CheckWX: {e}")
        checkwx_metars = []

    # VATSIM
    try:
        vatsim_metars = fetch_vatsim_metar(stations)
    except Exception as e:
        logger.error(f"Error fetching METAR data from VATSIM: {e}")
        vatsim_metars = []

    # Index METARs by station_id for each provider
    def index_by_station(metars):
        return {m["station_id"]: m for m in metars if m.get("station_id")}

    faa_indexed = index_by_station(faa_metars)
    checkwx_indexed = index_by_station(checkwx_metars)
    vatsim_indexed = index_by_station(vatsim_metars)

    final_metars = {}

    for stn in stations:
        candidates = []
        if stn in faa_indexed:
            candidates.append(("FAA", faa_indexed[stn]))
        if stn in checkwx_indexed:
            candidates.append(("CheckWX", checkwx_indexed[stn]))
        if stn in vatsim_indexed:
            candidates.append(("VATSIM", vatsim_indexed[stn]))

        if not candidates:
            logger.warning(f"No METAR data found for {stn} from any provider")
            continue

        # Always choose FAA if available
        faa_candidate = next((m for p, m in candidates if p == "FAA"), None)
        if faa_candidate:
            chosen_provider = "FAA"
            chosen_metar = faa_candidate
        else:
            # If FAA not available, then fall back to CheckWX, then VATSIM.
            # If CheckWX present:
            checkwx_candidate = next((m for p, m in candidates if p == "CheckWX"), None)
            if checkwx_candidate:
                chosen_provider = "CheckWX"
                chosen_metar = checkwx_candidate
            else:
                # else use VATSIM
                chosen_provider, chosen_metar = candidates[0]  # only VATSIM left

        logger.info(f"For {stn}, using METAR data from {chosen_provider}")
        final_metars[stn] = chosen_metar

    return final_metars


def store_yr_forecast_in_influxdb(forecast_data):
    """
    Fetch and store a forecast from yr.no in InfluxDB.
    :param forecast_data:  The forecast data dictionary.
    :return:
    """

    if "current_forecast" not in forecast_data or not forecast_data["current_forecast"]:
        logger.error("No current forecast data found in the forecast data.")
        return

    cf = forecast_data["current_forecast"]
    fields = {
        "temp_c": cf["temp_c"],
        "wind_speed_m_s": cf["wind_speed_m_s"],
        "cloud_fraction_percent": cf["cloud_fraction_percent"],
        "pressure_hpa": cf["pressure_hpa"],
        "relative_humidity_percent": cf["relative_humidity_percent"],
        "precip_1h_mm": cf["precip_1h_mm"],
        "precip_6h_mm": cf["precip_6h_mm"],
        "precip_12h_mm": cf["precip_12h_mm"]
    }
    tags = {"location": "Home"}

    try:
        write_measurement("yr_forecast", fields, tags)
        logger.info(f"Wrote yr.no forecast data to InfluxDB at {cf['observation_time']}")
    except Exception as e:
        logger.error(f"Failed to write yr.no forecast data to InfluxDB: {e}", exc_info=True)


def store_netatmo_to_influx(data):
    if not data:
        logger.warning("No netatmo data to store.")
        return

    fields = {
        "temperature_c": data["temperature"],
        "humidity_percent": data["humidity"],
        "pressure_hpa": data["pressure_hpa"],
        "rain_mm": data["rain_mm"]
    }
    # If wind data is present, add it
    if data.get("wind_strength_kmh") is not None:
        fields["wind_strength_kmh"] = data["wind_strength_kmh"]
    if data.get("wind_angle_deg") is not None:
        fields["wind_angle_deg"] = data["wind_angle_deg"]

    tags = {
        "station_name": data["station_name"]
    }

    try:
        write_measurement("netatmo", fields, tags)
        logger.info(f"Wrote Netatmo data for {data['station_name']} to InfluxDB")
    except Exception as e:
        logger.error(f"Failed to write Netatmo data to InfluxDB: {e}", exc_info=True)

    # Fetch Energy Prices
    fetch_energy_prices()



def main():
    stations = ["ENZV", "KJFK", "ENGM", "KLAX"]

    # Fetch METARs
    metars = get_airport_metars_from_providers(stations)

    # Write METAR Data to InfluxDB
    for station_id, metar in metars.items():
        fields = {
            "temp_c": metar["temp_c"],
            "dewpoint_c": metar["dewpoint_c"],
            "wind_dir_deg": metar["wind_dir_deg"],
            "wind_speed_kt": metar["wind_speed_kt"],
            "altim_in_hg": metar["altim_in_hg"],
            "altim_hpa": metar["altim_hpa"],
            "visibility_statute_mi": metar["visibility_statute_mi"]
        }
        tags = {
            "station_id": metar["station_id"]
        }
        try:
            write_measurement("metar", fields, tags)
            logger.info(
                f"{metar['station_id']}: Wrote METAR data to InfluxDB at {metar['observation_time']}. {metar['wx_string']}"
            )
        except Exception as e:
            logger.error(
                f"Failed to write METAR data for {metar['station_id']} to InfluxDB: {e}",
                exc_info=True
            )

    # Fetch and store forecast data from yr.no
    forecast_data = fetch_yr_forecast("59.9112", "10.7579")
    if forecast_data:
        store_yr_forecast_in_influxdb(forecast_data)
    else:
        logger.error("Failed to fetch forecast data from yr.no")


    # Fetch and store Netatmo data
    netatmo_data = fetch_netatmo_data()
    if netatmo_data:
        store_netatmo_to_influx(netatmo_data)
    else:
        logger.warning("No Netatmo data returned.")


if __name__ == "__main__":
    # For testing, just run once. Later we can add a schedule or loop.
    main()
    # Optional: if you want to run repeatedly:
    while True:
        main()
        time.sleep(300)  # wait 5 minutes
