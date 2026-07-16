import json
import urllib.request
from typing import Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Flight Service",port=8002)
BASE_URL = "https://standing-fish-574.convex.site"

def _get_json(url:str ):
    try:
        with urllib.request.urlopen(url,timeout=20) as response:
            data = response.read().decode("utf-8")
            return json.loads(data)
    except Exception as e:
        return {"error":True,"message":str(e)}

@mcp.tool()
def get_flights()-> list[dict]:
    """Get a list of all available fligts.
    Use this when the user asks to show/list all fligts.
    """
    url = f"{BASE_URL}/flights"
    data = _get_json(url)

    if isinstance(data,dict):
        return data.get("flights",[])
    return []

@mcp.tool()
def search_flights(origin:str,destination:str,date:Optional[str] = None)->list[dict]:
    """Search for flights by origin, destination and optional date.
    Args:
        origin: Origin city name.
        destination: Destination city name.
        date: Optional date in YYYY-MM-DD format.
    """
    url = f"{BASE_URL}/flights/search?origin={origin}&destination={destination}"
    if date:
        url += f"&date={date}"
    data = _get_json(url)
    if isinstance(data,dict):
        return data.get("flights",[])
    return []


@mcp.tool()
def book_flights(
    flight_id: str,
     passenger_name: str,
      passenger_email: str
      )->dict:  
    """Book a flight.
    Args:
        flight_id: ID of the flight to book
        passenger_name: Full name of the passenger
        passenger_email: Email of the passenger
    """
    payload = {
        "flightId":flight_id,
        "passengerName":passenger_name,
        "passengerEmail":passenger_email
    }

    data_bytes = json.dumps(payload).encode("utf-8")
    url = f"{BASE_URL}/flights/book"
    req = urllib.request.Request(url,data=data_bytes,headers={"Content-Type":"application/json"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=20) as response:
            result = response.read().decode("utf-8")
            return json.loads(result)
    except Exception as e :
        return {"error":True,"message":str(e)} 
    

if __name__ == "__main__":
    mcp.run(transport="streamable-http")