"""
Weather via Open-Meteo — completely free, no API key required.
Geocoding: https://geocoding-api.open-meteo.com
Forecast:  https://api.open-meteo.com
"""
import httpx

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes → human description
_WMO_CODES = {
    0: "clear sky",
    1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "icy fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    61: "light rain", 63: "moderate rain", 65: "heavy rain",
    71: "light snow", 73: "moderate snow", 75: "heavy snow",
    80: "light showers", 81: "moderate showers", 82: "violent showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "heavy thunderstorm with hail",
}


async def get_weather(city: str) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        # Step 1 — geocode city name to lat/lon
        geo_resp = await client.get(_GEOCODE_URL, params={"name": city, "count": 1, "language": "en", "format": "json"})
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        results = geo_data.get("results")
        if not results:
            return f"I couldn't find a location called {city}. Please check the spelling."

        loc = results[0]
        lat, lon = loc["latitude"], loc["longitude"]
        location_name = loc.get("name", city)
        country = loc.get("country", "")

        # Step 2 — fetch current weather
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weathercode,windspeed_10m",
            "wind_speed_unit": "kmh",
        }
        wx_resp = await client.get(_WEATHER_URL, params=params)
        wx_resp.raise_for_status()
        wx = wx_resp.json()["current"]

    temp        = round(wx["temperature_2m"])
    feels_like  = round(wx["apparent_temperature"])
    humidity    = wx["relative_humidity_2m"]
    wind        = round(wx["windspeed_10m"])
    description = _WMO_CODES.get(wx["weathercode"], "unknown conditions")

    return (
        f"Currently {temp}°C, feels like {feels_like}°C, and {description} "
        f"in {location_name}, {country}. "
        f"Humidity {humidity}%, wind {wind} km/h."
    )
