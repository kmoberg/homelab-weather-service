from fastapi import APIRouter, HTTPException
from src.database.influx_client import query_influx
from src.utils.config import Config
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/current")
def get_current_energy_price():
    # Get the current hour's price
    # We find the last record that is at or before now
    now = datetime.utcnow().isoformat() + "Z"
    flux = f'''
from(bucket: "{Config.INFLUX_BUCKET}")
  |> range(start: -1d)
  |> filter(fn: (r) => r._measurement == "energy_prices" and r._field == "eur_per_kwh" and r.region == "NO2")
  |> filter(fn: (r) => r._time <= now())
  |> last()
'''
    tables = query_influx(flux)
    if not tables or not tables[0].records:
        raise HTTPException(status_code=404, detail="No current energy price found")

    record = tables[0].records[0]
    return {
        "time": record.get_time().isoformat(),
        "eur_per_kwh": record.get_value()
    }

@router.get("/future")
def get_future_energy_prices():
    # Return future hours from now
    # Query data for next 36 hours or so, to cover today + tomorrow
    now = datetime.utcnow()
    flux = f'''
from(bucket: "{Config.INFLUX_BUCKET}")
  |> range(start: {now.isoformat()}Z, stop: { (now + timedelta(hours=48)).isoformat()}Z)
  |> filter(fn: (r) => r._measurement == "energy_prices" and r._field == "eur_per_kwh" and r.region == "NO2")
  |> group(columns: ["_time"])
  |> sort(columns: ["_time"], desc: false)
'''
    tables = query_influx(flux)
    if not tables:
        return []

    # Flatten results
    results = []
    for table in tables:
        for record in table.records:
            results.append({
                "time": record.get_time().isoformat(),
                "eur_per_kwh": record.get_value()
            })

    # If multiple results are returned, it's because we didn't limit by region or measure.
    # We did, so it should be unique. Just return them sorted.
    results.sort(key=lambda x: x["time"])
    return results