import json
import urllib.request
import urllib.parse
from typing import Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Weather Service", port=8004)

def _get_json(url: str):
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            data = response.read().decode("utf-8")
            return json.loads(data)
    except Exception as e:
        return {"error": True, "message": str(e)}

@mcp.tool()
def get_weather(city: str, date: Optional[str] = None) -> dict:
    """Get the weather conditions for a city and an optional date.
    
    Args:
        city: City name (e.g. Colombo, Mumbai, Paris).
        date: Optional check-in/travel date in YYYY-MM-DD format.
    """
    # 1. Try real-time API (wttr.in)
    safe_city = urllib.parse.quote(city)
    url = f"https://wttr.in/{safe_city}?format=j1"
    response = _get_json(url)
    
    if isinstance(response, dict) and "current_condition" in response:
        try:
            curr = response["current_condition"][0]
            temp = curr.get("temp_C", "N/A")
            humidity = curr.get("humidity", "N/A")
            wind = curr.get("windspeedKmh", "N/A")
            desc = curr.get("weatherDesc", [{}])[0].get("value", "N/A")
            
            return {
                "city": city,
                "date": date or "Today",
                "condition": desc,
                "temperature": f"{temp}°C",
                "humidity": f"{humidity}%",
                "wind": f"{wind} kph",
                "source": "wttr.in Live API"
            }
        except Exception:
            pass  # Fall back to mockup on parsing error
            
    # 2. Fallback to mock data if API is down or rate-limited
    city_lower = city.lower()
    seed = len(city_lower) + (ord(city_lower[0]) if city_lower else 0)
    conditions = ["Sunny", "Partly Cloudy", "Rainy", "Overcast", "Windy", "Stormy"]
    condition = conditions[seed % len(conditions)]
    
    temp_c = 15 + (seed % 20)  # 15 to 35 C
    humidity = 40 + (seed % 50)
    wind_kph = 5 + (seed % 25)
    
    if "colombo" in city_lower or "singapore" in city_lower or "bangkok" in city_lower:
        condition = "Humid" if (seed % 2 == 0) else "Tropical Sun"
        temp_c = 28 + (seed % 5)
    elif "mumbai" in city_lower:
        condition = "Monsoon Clouds" if (seed % 2 == 0) else "Humid and Sunny"
        temp_c = 30 + (seed % 3)

    return {
        "city": city,
        "date": date or "Today",
        "condition": condition,
        "temperature": f"{temp_c}°C",
        "humidity": f"{humidity}%",
        "wind": f"{wind_kph} kph",
        "source": "Mock Forecast Fallback"
    }

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
