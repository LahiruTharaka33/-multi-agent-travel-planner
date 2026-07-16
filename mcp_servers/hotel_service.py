import json
import urllib.request
from typing import Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Hotel Service",port=8001)
BASE_URL = "https://standing-fish-574.convex.site"

def _get_json(url: str):
    try:
        with urllib.request.urlopen(url,timeout=20) as response:
            data = response.read().decode("utf-8")
            return json.loads(data)
    except Exception as e:
        return {"error":True, "message":str(e)}
        

@mcp.tool()
def get_hotels() ->list[dict]:
    """Get a list of all available hotels.
    Use this when the user asks to show/list all hotels.
    """
    data = _get_json(f"{BASE_URL}/hotels")
    if isinstance (data,dict):
        return data.get("hotels",[])
    return []


@mcp.tool()
def search_hotels(city:str,check_in: Optional[str] = None, check_out: Optional[str] = None ) -> list[dict]:

    """Search for hotels by city and optional check-in/check-out dates.
    Args:
        city: Hotel city name. Example: Bangkok, Colombo, Singapore.
        checkIn: Optional check-in date in YYYY-MM-DD format.
        checkOut: Optional check-out date in YYYY-MM-DD format.
    """
    url = f"{BASE_URL}/hotels/search?city={city}"
    if check_in:
        url+= f"&checkIn={check_in}"
    if check_out:
        url+= f"&checkOut={check_out}"
    data = _get_json(url)
    if isinstance(data,dict):
        return data.get("hotels",[])
    return []

@mcp.tool()
def book_hotel(
    hotel_id:str,
    guest_name:str,
    guest_email:str,
    check_in_date:str,
    check_out_date:str,
    room_type:Optional[str] = None
) -> dict:
    """Book a hotel room.
        Args:
            hotel_id: ID of the hotel to book
            guest_name: Full name of the guest
            guest_email: Email of the guest
            check_in_date: Check-in date (YYYY-MM-DD)
            check_out_date: Check-out date (YYYY-MM-DD)
            room_type: Type of room (single, double, suite)
    """
    payload = {
        "hotelId":hotel_id,
        "guestName":guest_name,
        "guestEmail":guest_email,
        "checkInDate":check_in_date,
        "checkOutDate":check_out_date,
        "roomType":room_type
    }

    data_bytes = json.dumps(payload).encode("utf-8")
    url = f"{BASE_URL}/hotels/book"
    req = urllib.request.Request(url,data=data_bytes,headers={"Content-Type":"application/json"},method="POST")

    try:
        with urllib.request.urlopen(req,timeout=20) as response:
            result = response.read().decode("utf-8")
            return json.loads(result)
    except Exception as e:
        return {"error":True, "message":str(e)}

            
    
   






    






if __name__ == "__main__":
    mcp.run(transport="streamable-http")
