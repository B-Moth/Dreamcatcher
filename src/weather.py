import json
import urllib.request
from pathlib import Path


# ============================================================
# LOCATION
# ============================================================

# TODO: put your coordinates here
LATITUDE = 48.80
LONGITUDE = 2.49


# ============================================================
# FILE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

WEATHER_FILE = BASE_DIR / "data" / "weather.json"


# ============================================================
# WMO WEATHER CODE → OUR ANIMATION
# ============================================================

def weather_type(code):
    """
    Convert WMO weather codes into our animation categories.
    """

    # Clear
    if code == 0:
        return "sun"

    # Mainly clear / partly cloudy
    if code in (1, 2):
        return "cloud"

    # Overcast
    if code == 3:
        return "cloud"

    # Fog
    if code in (45, 48):
        return "fog"

    # Drizzle
    if code in (51, 53, 55, 56, 57):
        return "rain"

    # Rain
    if code in (61, 63, 65, 66, 67):
        return "rain"

    # Snow
    if code in (71, 73, 75, 77):
        return "snow"

    # Showers
    if code in (80, 81, 82):
        return "rain"

    # Snow showers
    if code in (85, 86):
        return "snow"

    # Thunderstorm
    if code in (95, 96, 99):
        return "storm"

    return "cloud"


# ============================================================
# GET CURRENT WEATHER
# ============================================================

def get_weather():

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LATITUDE}"
        f"&longitude={LONGITUDE}"
        "&current="
        "temperature_2m,"
        "weather_code,"
        "rain,"
        "snowfall,"
        "cloud_cover,"
        "is_day"
        "&timezone=auto"
    )

    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.load(response)

    current = data["current"]

    result = {
        "temperature": current["temperature_2m"],
        "weather_code": current["weather_code"],
        "weather": weather_type(current["weather_code"]),
        "rain": current["rain"],
        "snowfall": current["snowfall"],
        "cloud_cover": current["cloud_cover"],
        "is_day": current["is_day"],
        "time": current["time"],
    }

    return result


# ============================================================
# SAVE WEATHER
# ============================================================

def update_weather():

    try:
        weather = get_weather()

    except Exception as e:
        print(f"Weather update failed: {e}")

        if WEATHER_FILE.exists():
            with open(WEATHER_FILE, "r") as file:
                return json.load(file)

        return {
            "temperature": None,
            "weather_code": None,
            "weather": "cloud",
            "rain": 0,
            "snowfall": 0,
            "cloud_cover": 100,
            "is_day": 1,
            "time": None,
        }

    WEATHER_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(WEATHER_FILE, "w") as file:
        json.dump(
            weather,
            file,
            indent=4
        )

    return weather

# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    weather = update_weather()

    print("Weather updated:")
    print(f"  Condition : {weather['weather']}")
    print(f"  Temperature: {weather['temperature']} °C")
    print(f"  WMO code  : {weather['weather_code']}")
    print(f"  Rain      : {weather['rain']} mm")
    print(f"  Snow      : {weather['snowfall']} cm")
