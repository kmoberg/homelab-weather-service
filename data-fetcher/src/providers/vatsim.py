import requests
from src.utils.logging_config import logger


def fetch_vatsim_metar(stations):
    """
    Fetches METARs from VATSIM. The endpoint only supports one station at a time:
    https://metar.vatsim.net/metar.php?id=KJFK

    Returns a list of METAR dictionaries, one for each station.
    """
    if isinstance(stations, str):
        stations = [stations]

    metars = []

    for icao in stations:
        url = f"https://metar.vatsim.net/metar.php?id={icao}"
        logger.debug(f"Fetching METAR from VATSIM for {icao}: {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Error fetching VATSIM METAR for {icao}: {e}")
            continue

        raw_text = response.text.strip()
        # VATSIM returns just the raw METAR string, e.g. "KJFK 171451Z 25011KT ..."

        # We need to parse this METAR string. For simplicity, let’s do minimal parsing:
        # We'll use a simplified parser or just store raw for now.
        # In a real scenario, you might integrate a METAR parsing library.
        # For demonstration, let’s just extract a few fields using regex or assumptions.

        # This is a quick and dirty parse. For robust parsing, use a METAR library like python-metar.
        import re
        # A naive approach: split by space
        parts = raw_text.split()
        # Typically:
        # KJFK 171451Z 25011KT 8SM BKN012 ...
        # parts[0] = station
        # parts[1] = time like 171451Z (day=17 hour=14 min=51)
        station_id = parts[0]
        # Construct an observation time (naive, you can convert properly to a datetime)
        # Just store raw for now or store day/hour/min from parts[1]
        observation_time = None  # Not provided by VATSIM METAR directly with full date
        # For demonstration, leave None or parse from parts[1] if you know UTC date.

        # Find temperature: often after some fields like "12/10" for temp/dew
        temp_c = None
        dewpoint_c = None
        for p in parts:
            if "/" in p and len(p.split("/")) == 2:
                # e.g. "12/10" -> temp=12, dew=10
                t, d = p.split("/")
                try:
                    temp_c = float(t)
                    dewpoint_c = float(d)
                    break
                except:
                    pass

        # Wind:
        # e.g. "25011KT"
        wind_dir_deg = None
        wind_speed_kt = None
        for p in parts:
            if p.endswith("KT"):
                # format: dddffKT or dddffGggKT
                wind_match = re.match(r"(\d{3})(\d{2})", p)
                if wind_match:
                    wind_dir_deg = float(wind_match.group(1))
                    wind_speed_kt = float(wind_match.group(2))
                break

        # Altimeter might appear as Axxxx for inHg or Qxxxx for hPa
        altim_in_hg = None
        altim_hpa = None
        for p in parts:
            if p.startswith("A") and len(p) == 5:
                # A3014 means 30.14 inHg
                try:
                    alt = float(p[1:]) / 100.0
                    altim_in_hg = alt
                except:
                    pass
            elif p.startswith("Q") and len(p) == 5:
                # Q1014 means 1014 hPa
                try:
                    q = float(p[1:])
                    altim_hpa = q
                    altim_in_hg = q * 0.02953
                except:
                    pass

        # Visibility: e.g. "8SM"
        visibility_statute_mi = None
        for p in parts:
            if p.endswith("SM"):
                # e.g. "8SM"
                v = p.replace("SM", "")
                try:
                    visibility_statute_mi = float(v)
                except:
                    pass

        metars.append({
            "station_id": station_id,
            "observation_time": observation_time,
            "temp_c": temp_c,
            "dewpoint_c": dewpoint_c,
            "wind_dir_deg": wind_dir_deg,
            "wind_speed_kt": wind_speed_kt,
            "altim_in_hg": altim_in_hg,
            "altim_hpa": altim_hpa,
            "visibility_statute_mi": visibility_statute_mi,
            "wx_string": raw_text
        })

    return metars