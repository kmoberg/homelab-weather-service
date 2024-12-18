from fastapi import APIRouter, HTTPException
from src.database.influx_client import query_influx
from src.utils.config import Config

router = APIRouter()

def get_latest_point(measurement: str, fields: list[str], tags: dict[str, str] = None):
    # Build a Flux query to get the latest data point for given measurement and fields.
    # If tags are provided, filter by them.
    tag_filters = ""
    if tags:
        for k, v in tags.items():
            tag_filters += f' and r["{k}"] == "{v}"'
    fields_filter = ' or '.join([f'r._field == "{f}"' for f in fields])
    flux = f'''
from(bucket: "{Config.INFLUX_BUCKET}")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "{measurement}" {tag_filters} and ({fields_filter}))
  |> last()
'''
    tables = query_influx(flux)
    if not tables:
        return {}
    # Convert tables to a dict {field: value}
    data = {}
    for table in tables:
        for record in table.records:
            data[record.get_field()] = record.get_value()
    return data

@router.get("/metar/{station_id}")
def get_metar(station_id: str):
    fields = ["temp_c", "dewpoint_c", "wind_dir_deg", "wind_speed_kt", "altim_in_hg", "visibility_statute_mi", "wx_string"]
    data = get_latest_point("metar", fields, tags={"station_id": station_id})
    if not data:
        raise HTTPException(status_code=404, detail="No METAR data found")
    return data

@router.get("/forecast")
def get_forecast():
    fields = ["temp_c", "wind_speed_m_s", "cloud_fraction_percent", "pressure_hpa", "relative_humidity_percent", "precip_1h_mm", "precip_6h_mm", "precip_12h_mm"]
    data = get_latest_point("yr_forecast", fields)
    if not data:
        raise HTTPException(status_code=404, detail="No forecast data found")
    return data

@router.get("/netatmo")
def get_netatmo():
    fields = ["temperature_c", "humidity_percent", "pressure_hpa", "rain_mm", "wind_strength_kmh", "wind_angle_deg"]
    data = get_latest_point("netatmo", fields)
    if not data:
        raise HTTPException(status_code=404, detail="No Netatmo data found")
    return data

@router.get("/current")
def get_current():
    # Example: get a default station's METAR, plus forecast, plus netatmo
    # Change the default station as desired.
    default_station = "ENZV"
    metar_data = get_latest_point("metar", ["temp_c", "wind_speed_kt", "altim_hpa", "wx_string"], tags={"station_id":
                                                                                                            default_station})
    forecast_data = get_latest_point("yr_forecast", ["temp_c", "precip_1h_mm", "wind_speed_m_s"])
    netatmo_data = get_latest_point("netatmo", ["temperature_c", "humidity_percent", "rain_mm"])

    # Merge data into one response
    return {
        "metar": metar_data,
        "forecast": forecast_data,
        "netatmo": netatmo_data
    }