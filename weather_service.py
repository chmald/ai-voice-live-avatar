"""Weather service using the Open-Meteo API (free, no API key required).

Provides:
  - Geocoding via Open-Meteo Geocoding API
  - Current weather conditions via Open-Meteo Forecast API

Used as a function tool by the Voice Live session so the avatar can
answer weather questions conversationally.
"""

import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes → human-readable descriptions
_WMO_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow fall",
    73: "moderate snow fall",
    75: "heavy snow fall",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


def _parse_location(location: str) -> tuple[str, Optional[str], Optional[str]]:
    """Split a location string into (city, state_or_region, country).

    Handles formats like:
      "Seattle"                    → ("Seattle", None, None)
      "Portland, Oregon"          → ("Portland", "Oregon", None)
      "Paris, Île-de-France, France" → ("Paris", "Île-de-France", "France")
    """
    parts = [p.strip() for p in location.split(",") if p.strip()]
    city = parts[0] if parts else location
    state = parts[1] if len(parts) >= 2 else None
    country = parts[2] if len(parts) >= 3 else None
    return city, state, country


def _best_match(
    results: list[dict],
    state: Optional[str],
    country: Optional[str],
) -> dict:
    """Pick the result that best matches an optional state/country filter.

    Comparison is case-insensitive and supports substring matching so that
    "Oregon" matches admin1="Oregon" and "TX" matches admin1="Texas" etc.
    """
    def _norm(s: Optional[str]) -> str:
        return (s or "").lower().strip()

    if state:
        st = _norm(state)
        for r in results:
            admin1 = _norm(r.get("admin1"))
            # exact or substring match (covers abbreviations embedded in name)
            if st == admin1 or st in admin1 or admin1 in st:
                if country:
                    ct = _norm(country)
                    rc = _norm(r.get("country"))
                    if ct == rc or ct in rc or rc in ct:
                        return r
                else:
                    return r
        # Relax: match state only, ignore country
        for r in results:
            admin1 = _norm(r.get("admin1"))
            if st == admin1 or st in admin1 or admin1 in st:
                return r

    if country:
        ct = _norm(country)
        for r in results:
            rc = _norm(r.get("country"))
            if ct == rc or ct in rc or rc in ct:
                return r

    # No filter matched — fall back to first (most relevant) result
    return results[0]


async def geocode(location: str) -> Optional[dict]:
    """Resolve a location name to latitude/longitude via Open-Meteo Geocoding.

    Supports plain city names *and* "city, state" / "city, state, country"
    patterns.  The API only indexes by city name, so we search for the city
    part, fetch several candidates, and then pick the best match by
    state/region and country.

    Returns ``{"name", "lat", "lon", "country", "admin1"}`` or ``None``.
    """
    city, state, country = _parse_location(location)

    # Fetch more candidates when we need to filter by state/country
    count = 10 if state or country else 1

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(_GEOCODING_URL, params={"name": city, "count": count})
        resp.raise_for_status()
        data = resp.json()

    results = data.get("results")
    if not results:
        return None

    r = _best_match(results, state, country)
    return {
        "name": r.get("name", city),
        "lat": r["latitude"],
        "lon": r["longitude"],
        "country": r.get("country", ""),
        "admin1": r.get("admin1", ""),  # state / region
    }


async def get_current_weather(lat: float, lon: float) -> dict:
    """Fetch current weather conditions for a coordinate pair.

    Returns a dict with temperature, conditions, wind, humidity, etc.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "weather_code",
            "wind_speed_10m",
            "wind_gusts_10m",
            "precipitation",
        ]),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(_FORECAST_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    current = data.get("current", {})
    weather_code = current.get("weather_code", -1)

    return {
        "temperature_f": current.get("temperature_2m"),
        "feels_like_f": current.get("apparent_temperature"),
        "humidity_pct": current.get("relative_humidity_2m"),
        "conditions": _WMO_CODES.get(weather_code, "unknown"),
        "wind_speed_mph": current.get("wind_speed_10m"),
        "wind_gusts_mph": current.get("wind_gusts_10m"),
        "precipitation_inch": current.get("precipitation"),
    }


def _format_weather(place: str, weather: dict) -> str:
    """Format a weather dict into a human-readable summary string."""
    return (
        f"Current weather in {place}: "
        f"{weather['conditions']}, "
        f"{weather['temperature_f']}°F (feels like {weather['feels_like_f']}°F), "
        f"humidity {weather['humidity_pct']}%, "
        f"wind {weather['wind_speed_mph']} mph "
        f"(gusts {weather['wind_gusts_mph']} mph), "
        f"precipitation {weather['precipitation_inch']} in."
    )


async def reverse_geocode(lat: float, lon: float) -> str:
    """Best-effort reverse geocode: find the nearest city name for coordinates.

    Uses Open-Meteo geocoding search with a synthetic query, falling back
    to a simple lat/lon label.
    """
    try:
        # Open-Meteo doesn't have a true reverse-geocode endpoint, so
        # we use the forecast response's timezone / location metadata.
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                _FORECAST_URL,
                params={"latitude": lat, "longitude": lon, "current": "temperature_2m"},
            )
            resp.raise_for_status()
            data = resp.json()
        # The API returns timezone which often contains "Area/City"
        tz = data.get("timezone", "")
        if "/" in tz:
            return tz.split("/")[-1].replace("_", " ")
    except Exception:
        pass
    return f"{lat:.2f}°N, {lon:.2f}°W"


async def get_weather(location: str) -> str:
    """High-level helper: geocode a location and return a weather summary string.

    This is the function invoked by the Voice Live tool-call handler.
    Returns a human-readable string the model can paraphrase.
    """
    try:
        geo = await geocode(location)
        if not geo:
            return f"Could not find location: {location}"

        weather = await get_current_weather(geo["lat"], geo["lon"])

        region = geo["admin1"]
        country = geo["country"]
        place = geo["name"]
        if region:
            place = f"{place}, {region}"
        if country:
            place = f"{place}, {country}"

        return _format_weather(place, weather)
    except Exception as e:
        logger.error(f"Weather lookup failed for '{location}': {e}", exc_info=True)
        return f"Sorry, I couldn't retrieve weather data for {location}. Error: {e}"


async def get_weather_by_coords(lat: float, lon: float) -> str:
    """Fetch weather using raw coordinates (from browser geolocation).

    Used when the user asks about weather 'near me' / 'in my area' and
    the frontend has provided GPS coordinates.
    """
    try:
        weather = await get_current_weather(lat, lon)
        place = await reverse_geocode(lat, lon)
        return _format_weather(place, weather)
    except Exception as e:
        logger.error(f"Weather lookup failed for ({lat}, {lon}): {e}", exc_info=True)
        return f"Sorry, I couldn't retrieve weather data for your location. Error: {e}"
