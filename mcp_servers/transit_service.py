import os
import json
import urllib.request
import urllib.parse
from typing import Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Transit Service", port=8005)

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
def get_transit_options(origin: str, destination: str) -> list:
    """Get public transit routing options between an origin and a destination.
    
    Args:
        origin: Point of departure (e.g. London, Colombo).
        destination: Point of arrival (e.g. Paris, Katunayake).
    """
    gmaps_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    
    # 1. Try real-time Google Maps API if key is present
    if gmaps_key and gmaps_key != "fake_key":
        encoded_origin = urllib.parse.quote(origin)
        encoded_dest = urllib.parse.quote(destination)
        url = f"https://maps.googleapis.com/maps/api/directions/json?origin={encoded_origin}&destination={encoded_dest}&mode=transit&key={gmaps_key}"
        
        response = _get_json(url)
        
        if isinstance(response, dict) and response.get("status") == "OK" and response.get("routes"):
            try:
                routes = []
                for i, r in enumerate(response["routes"]):
                    leg = r["legs"][0]
                    duration = leg.get("duration", {}).get("text", "N/A")
                    distance = leg.get("distance", {}).get("text", "N/A")
                    
                    steps = []
                    for step in leg.get("steps", []):
                        inst = step.get("html_instructions", "")
                        # Simple html tag stripping
                        clean_inst = ""
                        in_tag = False
                        for char in inst:
                            if char == "<":
                                in_tag = True
                            elif char == ">":
                                in_tag = False
                            elif not in_tag:
                                clean_inst += char
                        steps.append(clean_inst)
                    
                    # Estimate a fake price based on route distance/steps
                    price_est = 15 + (len(steps) * 5)
                    
                    routes.append({
                        "origin": leg.get("start_address", origin),
                        "destination": leg.get("end_address", destination),
                        "mode": "Public Transit (Google Maps)",
                        "duration": duration,
                        "distance": distance,
                        "steps": steps[:4], # Top 4 steps
                        "price": f"${price_est}",
                        "source": "Google Maps API"
                    })
                return routes
            except Exception:
                pass  # Fall back on parsing/formatting failure
                
    # 2. Fallback to simulated transit db
    orig_lower = origin.lower()
    dest_lower = destination.lower()
    
    # Pre-defined high frequency route simulations
    if "london" in orig_lower and "paris" in dest_lower:
        return [
            {
                "origin": "London St Pancras",
                "destination": "Paris Gare du Nord",
                "mode": "Eurostar Train",
                "duration": "2h 16m",
                "distance": "213 miles",
                "steps": [
                    "Board Eurostar train at London St Pancras Int.",
                    "Direct transit through the Channel Tunnel",
                    "Arrive at Paris Gare du Nord"
                ],
                "price": "$98",
                "source": "Mock Transit database"
            },
            {
                "origin": "London Heathrow (LHR)",
                "destination": "Paris Charles de Gaulle (CDG)",
                "mode": "Flight & Subway",
                "duration": "4h 30m",
                "distance": "230 miles",
                "steps": [
                    "Take Piccadilly Line to Heathrow Airport",
                    "Fly from London (LHR) to Paris (CDG)",
                    "Take RER B train to Paris center"
                ],
                "price": "$125",
                "source": "Mock Transit database"
            }
        ]
        
    if "colombo" in orig_lower or "colombo" in dest_lower:
        return [
            {
                "origin": origin,
                "destination": destination,
                "mode": "AC Intercity Express Bus",
                "duration": "1h 15m",
                "distance": "32 km",
                "steps": [
                    "Board Colombo-Katunayake Express Bus (E03)",
                    "Transit via Airport Expressway",
                    "Arrive at destination terminal"
                ],
                "price": "$3.50",
                "source": "Mock Transit database"
            },
            {
                "origin": origin,
                "destination": destination,
                "mode": "Standard Train / Taxi combo",
                "duration": "1h 45m",
                "distance": "35 km",
                "steps": [
                    "Take Train from Fort Railway Station to Liyanagemulla",
                    "Take local Tuk-tuk/Taxi local ride to final destination"
                ],
                "price": "$12.00",
                "source": "Mock Transit database"
            }
        ]
        
    if "mumbai" in orig_lower or "mumbai" in dest_lower:
        return [
            {
                "origin": origin,
                "destination": destination,
                "mode": "Mumbai Suburban Railway (Local Train)",
                "duration": "1h 10m",
                "distance": "45 km",
                "steps": [
                    "Board fast local train from CSMT to Kalyan",
                    "Take local auto-rickshaw to destination"
                ],
                "price": "$1.50",
                "source": "Mock Transit database"
            },
            {
                "origin": origin,
                "destination": destination,
                "mode": "Ola / Uber Cab Service",
                "duration": "1h 40m",
                "distance": "40 km",
                "steps": [
                    "Book cab via ride-hailing app",
                    "Transit via Eastern Express Highway"
                ],
                "price": "$18.50",
                "source": "Mock Transit database"
            }
        ]

    # Dynamic fallback on any generic input
    seed = len(orig_lower) + len(dest_lower)
    fake_hours = (seed % 4) + 1
    fake_mins = (seed % 60)
    fake_price = 10 + (seed % 40)
    
    return [
        {
            "origin": origin,
            "destination": destination,
            "mode": "Intercity Public Bus",
            "duration": f"{fake_hours}h {fake_mins}m",
            "distance": f"{(seed * 8) % 150} km",
            "steps": [
                f"Board transit regional bus from {origin} central station",
                f"Travel along highway system",
                f"Disembark at {destination} visitor terminal"
            ],
            "price": f"${fake_price}.00",
            "source": "Mock Transit database"
        },
        {
            "origin": origin,
            "destination": destination,
            "mode": "Private Car Rental / Taxi",
            "duration": f"{max(1, fake_hours - 1)}h {fake_mins}m",
            "distance": f"{(seed * 8) % 150} km",
            "steps": [
                "Book private ride-hail or rent-a-cab",
                "Direct navigation along fastest path"
            ],
            "price": f"${fake_price * 4}.00",
            "source": "Mock Transit database"
        }
    ]

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
