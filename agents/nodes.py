import json
import logging
from typing import Optional, Literal

logger = logging.getLogger("agents")

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from .mcp_client import hotel_mcp_tools, flight_mcp_tools, weather_mcp_tools, transit_mcp_tools
from .llm import llm
from .prompts import get_system_prompt_with_history, get_system_prompt_for_unknown_node
from .entity import GraphState


class TravelExtraction(BaseModel):
    intent: Literal["hotel", "flight", "unknown", "plan", "weather", "transit"] = Field(
        default="unknown",
        description="Main user intent: hotel, flight, weather, transit or unknown."
    )

    sub_action: Literal["search", "list_all","book", "general"] = Field(
        default="general",
        description="Action type: search, list_all, book or general."
    )

    city: Optional[str] = Field(
        default=None,
        description="Hotel city name. Example: Mumbai, Colombo, Bangkok."
    )

    check_in: Optional[str] = Field(
        default=None,
        description="Hotel check-in date in YYYY-MM-DD format. Null if not provided."
    )

    check_out: Optional[str] = Field(
        default=None,
        description="Hotel check-out date in YYYY-MM-DD format. Null if not provided."
    )

    origin: Optional[str] = Field(
        default=None,
        description="Flight origin city or airport code. Example: BOM, CMB, Mumbai."
    )

    destination: Optional[str] = Field(
        default=None,
        description="Flight destination city or airport code. Example: DEL, BKK, Delhi."
    )

    flight_date: Optional[str] = Field(
        default=None,
        description="Flight date in YYYY-MM-DD format. Null if not provided."
    )
    hotel_id: Optional[str] = Field(
        default=None,
        description="ID of the hotel to book. Null if not provided."
    )

    guest_name: Optional[str] = Field(
        default=None,
        description="Guest full name for hotel booking. Null if not provided."
    )

    guest_email: Optional[str] = Field(
        default=None,
        description="Guest email for hotel booking. Null if not provided."
    )

    room_type: Optional[str] = Field(
        default=None,
        description="Hotel room type such as single, double, or suite. Null if not provided."
    )
    flight_id: Optional[str] = Field(
        default=None,
        description="ID of the flight to book. Null if not provided."
    )

    passenger_name: Optional[str] = Field(
        default=None,
        description="Passenger full name for flight booking. Null if not provided."
    )

    passenger_email: Optional[str] = Field(
        default=None,
        description="Passenger email for flight booking. Null if not provided."
    )


travel_extractor = llm.with_structured_output(TravelExtraction)

def _merge(new_val, old_val):
    """Return new_val if it's set, otherwise keep old_val."""
    return new_val if new_val is not None else old_val


def router(state: GraphState) -> dict:
    user_message = state["messages"][-1]
    history_messages = state["messages"][:-1]
    
    system_prompt = get_system_prompt_with_history("\n".join(history_messages))

    invocation_messages = [SystemMessage(content=system_prompt)]
    for i in range(0, len(history_messages), 2):
        invocation_messages.append(HumanMessage(content=history_messages[i]))
        if i + 1 < len(history_messages):
            invocation_messages.append(AIMessage(content=history_messages[i + 1]))
    invocation_messages.append(HumanMessage(content=user_message))

    try:
        extracted = travel_extractor.invoke(invocation_messages)

        data = extracted.dict()
        logger.info(f"Router extracted intent: {data.get('intent')} | sub_action: {data.get('sub_action')}")

    except Exception as e:
        logger.error(f"Router LLM extraction failed: {e}")
        data = {
            "intent": "unknown",
            "sub_action": "general",
            "city": None,
            "check_in": None,
            "check_out": None,
            "origin": None,
            "destination": None,
            "flight_date": None,
            "hotel_id": None,
            "guest_name": None,
            "guest_email": None,
            "room_type": None,
        }

    return {
        
        "intent": _merge(data.get("intent") if data.get("intent") != "unknown" else None, state.get("intent")),
        "sub_action": data.get("sub_action", "general"),
    
        "city":     _merge(data.get("city"),        state.get("city")),
        "check_in": _merge(data.get("check_in"),    state.get("check_in")),
        "check_out": _merge(data.get("check_out"),  state.get("check_out")),
    
        "origin":      _merge(data.get("origin"),      state.get("origin")),
        "destination": _merge(data.get("destination"), state.get("destination")),
        "flight_date": _merge(data.get("flight_date"), state.get("flight_date")),
    
        "hotel_id":   _merge(data.get("hotel_id"),   state.get("hotel_id")),
        "guest_name": _merge(data.get("guest_name"), state.get("guest_name")),
        "guest_email": _merge(data.get("guest_email"), state.get("guest_email")),
        "room_type":  _merge(data.get("room_type"),  state.get("room_type")),
    
        "flight_id":        _merge(data.get("flight_id"),       state.get("flight_id")),
        "passenger_name":   _merge(data.get("passenger_name"),  state.get("passenger_name")),
        "passenger_email":  _merge(data.get("passenger_email"), state.get("passenger_email")),
    
        "hotel_results": [],
        "flight_results": [],
        "response_text": "",
    }





def _parse_mcp_result(result) -> list:
    """Normalize an MCP tool result into a plain list of dicts.

    langchain_mcp_adapters may return any of:
    - plain list of dicts                              (ideal)
    - JSON string of a list or dict                    (string-serialized)
    - list of TextContent dicts: [{"type","text":...}] (MCP content blocks)
    """
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            return []

    if isinstance(result, list):
        items: list = []
        for item in result:
            if isinstance(item, dict) and "text" in item:
                try:
                    inner = json.loads(item["text"])
                    if isinstance(inner, list):
                        items.extend(inner)
                    elif isinstance(inner, dict):
                        items.append(inner)
                except Exception:
                    items.append(item)
            elif isinstance(item, str):
                try:
                    inner = json.loads(item)
                    if isinstance(inner, list):
                        items.extend(inner)
                    elif isinstance(inner, dict):
                        items.append(inner)
                except Exception:
                    pass
            elif isinstance(item, dict):
                items.append(item)
        return items

    if isinstance(result, dict):
        return [result]

    return []


def _format_weather(report: dict) -> str:
    city = report.get("city", "Unknown")
    date = report.get("date", "N/A")
    condition = report.get("condition", "N/A")
    temp = report.get("temperature", "N/A")
    humidity = report.get("humidity", "N/A")
    wind = report.get("wind", "N/A")
    source = report.get("source", "")
    src_str = f" (via {source})" if source else ""
    
    return (
        f"🌡️ **{city} Weather ({date}){src_str}:**\n"
        f"- Condition: {condition}\n"
        f"- Temperature: {temp}\n"
        f"- Humidity: {humidity}\n"
        f"- Wind: {wind}"
    )


def _format_transit(route: dict) -> str:
    origin = route.get("origin", "N/A")
    destination = route.get("destination", "N/A")
    mode = route.get("mode", "N/A")
    duration = route.get("duration", "N/A")
    distance = route.get("distance", "N/A")
    price = route.get("price", "N/A")
    steps = route.get("steps", [])
    steps_str = "\n  - " + "\n  - ".join(steps) if steps else ""
    return (
        f"➡️ **{mode} ({duration}, {distance})** - Est: {price}\n"
        f"  Path: {origin} to {destination}{steps_str}"
    )


def _format_hotel(hotel: dict) -> str:

    name = hotel.get("name", "Unknown hotel")

    city_data = hotel.get("city", "unknown city")
    if isinstance(city_data, dict):
        city = city_data.get("name", "unknown city")
    else:
        city = city_data

    stars = hotel.get("starRating", hotel.get("stars", hotel.get("rating", "N/A")))
    price = hotel.get("price", hotel.get("pricePerNight", "N/A"))
    currency = hotel.get("currency", "USD")

    available = hotel.get(
        "available_rooms",
        hotel.get("availableRooms", hotel.get("available", "N/A"))
    )

    return (
        f"{name} in {city}, "
        f"{stars} stars - {currency} {price}/night - "
        f"{available} rooms"
    )


def _format_flight(flight: dict) -> str:
    airline = flight.get("airline", "Unknown airline")

    number = flight.get(
        "flightNumber",
        flight.get("flight_number", flight.get("flightNo", "N/A"))
    )

    origin_data = flight.get("origin", "unknown")
    destination_data = flight.get("destination", "unknown")

    if isinstance(origin_data, dict):
        origin = origin_data.get("airport", origin_data.get("city", "unknown"))
    else:
        origin = origin_data

    if isinstance(destination_data, dict):
        destination = destination_data.get("airport", destination_data.get("city", "unknown"))
    else:
        destination = destination_data

    flight_date = flight.get(
        "flightDate",
        flight.get("date", flight.get("departure_date", "unknown"))
    )

    departure_time = flight.get(
        "departureTime",
        flight.get("departure_time", "N/A")
    )

    arrival_time = flight.get(
        "arrivalTime",
        flight.get("arrival_time", "N/A")
    )

    price = flight.get("price", "N/A")
    currency = flight.get("currency", "USD")

    seats = flight.get(
        "availableSeats",
        flight.get("available_seats", flight.get("seats", "N/A"))
    )

    return (
        f"{airline} {number} from {origin} to {destination} "
        f"on {flight_date}, {departure_time} - {arrival_time} "
        f"- {currency} {price} - {seats} seats"
    )



async def hotel_node(state: GraphState) -> dict:
    city = state.get("city")
    check_in = state.get("check_in")
    check_out = state.get("check_out")

    if state.get("sub_action") == "book":
        hotel_id = state.get("hotel_id")
        guest_name = state.get("guest_name")
        guest_email = state.get("guest_email")
        room_type = state.get("room_type")
        check_in_date = state.get("check_in")
        check_out_date = state.get("check_out")

        missing = [
            field for field, value in [
                ("hotel_id", hotel_id), ("guest_name", guest_name), ("guest_email", guest_email), 
                ("check_in", check_in_date), ("check_out", check_out_date), ("room_type", room_type)
            ] if not value
        ]

        if missing:
            logger.info(f"hotel_node missing booking fields: {missing}")
            return {
                "hotel_results": [],
                "flight_results": [],
                "response_text": (
                    "I need more details to book the hotel. "
                    "Please provide hotel_id, guest_name, guest_email, room_type, "
                    "check_in, and check_out."
                ),
            }

        try:
            async with hotel_mcp_tools() as tools:
                result = await tools["book_hotel"].ainvoke(
                    {
                        "hotel_id": hotel_id,
                        "guest_name": guest_name,
                        "guest_email": guest_email,
                        "check_in_date": check_in_date,
                        "check_out_date": check_out_date,
                        "room_type": room_type,
                    })

        except Exception as e:
            return {
                "hotel_results": [],
                "flight_results": [],
                "response_text": "I'm having trouble connecting to the hotel service. Please try again later."
            }   
            

        if isinstance(result, dict):
            confirmation = result.get("message") or result.get("status") or "Hotel booking completed."
            return {
                "hotel_results": [],
                "flight_results": [],
                "response_text": confirmation,
            }

        return {
            "hotel_results": [],
            "flight_results": [],
            "response_text": "Hotel booking completed.",
        }

    elif city:
        params = {"city": city}
        if check_in:
            params["checkIn"] = check_in
        if check_out:
            params["checkOut"] = check_out

        try:
            async with hotel_mcp_tools() as tools:
                result = await tools["search_hotels"].ainvoke(params)
        except Exception as e:
            return {
                "hotel_results": [],
                "flight_results":[],
                "response_text": "I'm having trouble connecting to the hotel service. Please try again later."
            }        

    else:
        try:
            logger.info("Fetching all hotels...")
            async with hotel_mcp_tools() as tools:
                result = await tools["get_hotels"].ainvoke({})
        except Exception as e:
            return {
                "hotel_results": [],
                "flight_results":[],
                "response_text": "I'm having trouble connecting to the hotel service. Please try again later."
            }        
        

    hotel_results = _parse_mcp_result(result)

    if not hotel_results:
        return {
            "hotel_results": [],
            "flight_results": [],
            "response_text": (
                "I couldn't find any hotels. "
                "Try searching by city, for example: 'available hotels in Mumbai'."
            ),
        }

    return {
        "hotel_results": hotel_results,
        "flight_results": [],
        "response_text": "",
    }


async def flight_node(state: GraphState) -> dict:
    origin = state.get("origin")
    destination = state.get("destination")
    flight_date = state.get("flight_date")

    if state.get("sub_action") == "book":
        flight_id = state.get("flight_id")
        passenger_name = state.get("passenger_name")
        passenger_email = state.get("passenger_email")

        missing = [
            field
            for field, value in [
                ("flight_id", flight_id),
                ("passenger_name", passenger_name),
                ("passenger_email", passenger_email),
            ]
            if not value
        ]

        if missing:
            return {
                "hotel_results": [],
                "flight_results": [],
                "response_text": (
                    "I need more details to book the flight. "
                    "Please provide flight_id, passenger_name, and passenger_email."
                ),
            }

        try:
            async with flight_mcp_tools() as tools:
                result = await tools["book_flights"].ainvoke(
                    {
                        "flight_id": flight_id,
                        "passenger_name": passenger_name,
                        "passenger_email": passenger_email,
                    }
                )
        except Exception as e:
            return {
                "hotel_results": [],
                "flight_results": [],
                "response_text": "I'm having trouble connecting to the flight service. Please try again later."
            }

        if isinstance(result, dict):
            confirmation = result.get("message") or result.get("status") or "Flight booking completed."
            return {
                "flight_results": [],
                "response_text": confirmation,
            }

        return {
            "flight_results": [],
            "response_text": "Flight booking completed.",
        }

    elif origin and destination:
        params = {"origin": origin, "destination": destination}
        if flight_date:
            params["date"] = flight_date

        try:
            async with flight_mcp_tools() as tools:
                result = await tools["search_flights"].ainvoke(params)
        except Exception as e:
            return{
                "hotel_results": [],
                "flight_results": [],
                "response_text": "I'm having trouble connecting to the flight service. Please try again later."
            }        

    elif origin or destination:
        return {
            "hotel_results": [],
            "flight_results": [],
            "response_text": (
                "I need both departure and destination information. "
                "For example: 'flight from BOM to DEL'."
            ),
        }

    else:
        try:
            logger.info("Fetching all flights...")
            async with flight_mcp_tools() as tools:
                result = await tools["get_flights"].ainvoke({})
        except Exception as e:
            return {
                "hotel_results":[],
                "flight_results":[],
                "response_text":"I'm having trouble connecting to the flight service. Please try again later."
            }
        

    flight_results = _parse_mcp_result(result)

    if not flight_results:
        return {
            "hotel_results": [],
            "flight_results": [],
            "response_text": (
                "I couldn't find flights matching your request. "
                "Try another route or ask for all flights."
            ),
        }

    return {
        "hotel_results": [],
        "flight_results": flight_results,
        "response_text": "",
    }


async def planner_node(state: GraphState) -> dict:
    city = state.get("city")
    check_in = state.get("check_in")
    origin = state.get("origin")
    flight_date = state.get("flight_date")
    destination = state.get("destination") or city
    
    missing = []
    if not city: missing.append("destination city")
    if not check_in: missing.append("check-in date")
    if not origin: missing.append("flight origin")
    if not flight_date: missing.append("flight date")

    if missing:
        return {
            "hotel_results": [],
            "flight_results": [],
            "response_text": f"I need a few more details to plan your trip. Please provide: {', '.join(missing)}.",
        }

    # Fetch hotels
    hotel_res = []
    try:
        logger.info(f"Planner fetching hotels in {city}...")
        hotel_params = {"city": city, "checkIn": check_in}
        if state.get("check_out"):
            hotel_params["checkOut"] = state.get("check_out")
        async with hotel_mcp_tools() as tools:
            h_result = await tools["search_hotels"].ainvoke(hotel_params)
            hotel_res = _parse_mcp_result(h_result)
    except Exception:
        pass

    # Fetch flights
    flight_res = []
    try:
        logger.info(f"Planner fetching flights {origin} to {destination}...")
        flight_params = {"origin": origin, "destination": destination, "date": flight_date}
        async with flight_mcp_tools() as tools:
            f_result = await tools["search_flights"].ainvoke(flight_params)
            flight_res = _parse_mcp_result(f_result)
    except Exception:
        pass

    # Fetch weather
    weather_res = []
    try:
        logger.info(f"Planner fetching weather forecast in {city}...")
        w_params = {"city": city}
        if check_in:
            w_params["date"] = check_in
        async with weather_mcp_tools() as tools:
            w_result = await tools["get_weather"].ainvoke(w_params)
            weather_res = _parse_mcp_result(w_result)
    except Exception as e:
        logger.error(f"Planner fetching weather failed: {e}")
        pass

    # Fetch transit
    transit_res = []
    try:
        if origin and destination:
            logger.info(f"Planner fetching transit from {origin} to {destination}...")
            t_params = {"origin": origin, "destination": destination}
            async with transit_mcp_tools() as tools:
                t_result = await tools["get_transit_options"].ainvoke(t_params)
                transit_res = _parse_mcp_result(t_result)
    except Exception as e:
        logger.error(f"Planner fetching transit failed: {e}")
        pass

    if not hotel_res and not flight_res:
        return {
            "hotel_results": [],
            "flight_results": [],
            "weather_results": weather_res,
            "transit_results": transit_res,
            "response_text": "I couldn't find any hotels or flights for your trip. Please try different dates or locations.",
        }

    return {
        "hotel_results": hotel_res,
        "flight_results": flight_res,
        "weather_results": weather_res,
        "transit_results": transit_res,
        "response_text": "",
    }


async def weather_node(state: GraphState) -> dict:
    city = state.get("city")
    check_in = state.get("check_in")
    flight_date = state.get("flight_date")
    date = flight_date or check_in

    if not city:
        return {
            "weather_results": [],
            "response_text": "Please tell me which city you want weather information for.",
        }

    weather_res = []
    try:
        logger.info(f"Fetching weather for {city}...")
        params = {"city": city}
        if date:
            params["date"] = date
        async with weather_mcp_tools() as tools:
            result = await tools["get_weather"].ainvoke(params)
            weather_res = _parse_mcp_result(result)
    except Exception as e:
        logger.error(f"Weather service tool failed: {e}")
        return {
            "weather_results": [],
            "response_text": f"I'm having trouble connecting to the weather service. Error: {str(e)}",
        }

    return {
        "weather_results": weather_res,
        "response_text": "",
    }


async def transit_node(state: GraphState) -> dict:
    origin = state.get("origin")
    destination = state.get("destination")
    city = state.get("city")

    actual_origin = origin or city or "London"
    actual_dest = destination or city or "Paris"

    transit_res = []
    try:
        logger.info(f"Fetching transit from {actual_origin} to {actual_dest}...")
        params = {"origin": actual_origin, "destination": actual_dest}
        async with transit_mcp_tools() as tools:
            result = await tools["get_transit_options"].ainvoke(params)
            transit_res = _parse_mcp_result(result)
    except Exception as e:
        logger.error(f"Transit service tool failed: {e}")
        return {
            "transit_results": [],
            "response_text": f"I'm having trouble connecting to the transit service. Error: {str(e)}",
        }

    return {
        "transit_results": transit_res,
        "response_text": "",
    }


def unknown_node(state: GraphState) -> dict:
    user_message = state["messages"][-1]
    history_messages = state["messages"][:-1]

    system_prompt = get_system_prompt_for_unknown_node("\n".join(history_messages))

    invocation_messages = [SystemMessage(content=system_prompt)]
    for i in range(0, len(history_messages), 2):
        invocation_messages.append(HumanMessage(content=history_messages[i]))
        if i + 1 < len(history_messages):
            invocation_messages.append(AIMessage(content=history_messages[i + 1]))
    invocation_messages.append(HumanMessage(content=user_message))

    try:
        response = llm.invoke(invocation_messages)

        return {
            "hotel_results": [],
            "flight_results": [],
            "response_text": response.content,
        }

    except Exception as e:
        return {
            "hotel_results": [],
            "flight_results": [],
            "response_text": f"I couldn't understand your request clearly. Error: {str(e)}",
        }



def generate_response(state: GraphState) -> dict:
    if state.get("response_text"):
        return {
            "response_text": state["response_text"]
        }

    hotel_results = state.get("hotel_results", [])
    flight_results = state.get("flight_results", [])
    weather_results = state.get("weather_results", [])
    transit_results = state.get("transit_results", [])

    if state.get("intent") == "plan":
        h_lines = [_format_hotel(h) for h in hotel_results[:5]] if hotel_results else ["No hotels found for this route/date."]
        f_lines = [_format_flight(f) for f in flight_results[:5]] if flight_results else ["No flights found for this route/date."]
        w_lines = [_format_weather(w) for w in weather_results[:5]] if weather_results else ["No weather info found for this route/date."]
        t_lines = [_format_transit(t) for t in transit_results[:5]] if transit_results else ["No transit routing info found for this route/date."]
        
        return {
            "hotel_results": hotel_results,
            "flight_results": flight_results,
            "weather_results": weather_results,
            "transit_results": transit_results,
            "response_text": (
                f"**Here's your Trip Plan:**\n\n"
                f"✈️ **Flights ({len(flight_results)} options):**\n" + "\n".join(f_lines) + "\n\n"
                f"🏨 **Hotels ({len(hotel_results)} options):**\n" + "\n".join(h_lines) + "\n\n"
                f"🌤️ **Weather Forecast:**\n" + "\n".join(w_lines) + "\n\n"
                f"🚊 **Transit/Routes Info:**\n" + "\n".join(t_lines)
            )
        }

    if state.get("intent") == "weather" or (weather_results and not hotel_results and not flight_results and not transit_results):
        w_lines = [_format_weather(w) for w in weather_results[:5]]
        return {
            "weather_results": weather_results,
            "response_text": (
                f"Here is the weather forecast:\n"
                + "\n".join(w_lines)
            )
        }

    if state.get("intent") == "transit" or (transit_results and not hotel_results and not flight_results):
        t_lines = [_format_transit(t) for t in transit_results[:5]]
        return {
            "transit_results": transit_results,
            "response_text": (
                f"Here are the transit/routes options:\n"
                + "\n".join(t_lines)
            )
        }

    if hotel_results and flight_results:
        h_lines = [_format_hotel(h) for h in hotel_results[:5]]
        f_lines = [_format_flight(f) for f in flight_results[:5]]
        return {
            "hotel_results": hotel_results,
            "flight_results": flight_results,
            "response_text": (
                f"**Here's your Trip Plan:**\n\n"
                f"✈️ **Flights ({len(flight_results)} options):**\n" + "\n".join(f_lines) + "\n\n"
                f"🏨 **Hotels ({len(hotel_results)} options):**\n" + "\n".join(h_lines)
            )
        }

    if hotel_results:
        count = len(hotel_results)
        lines = [_format_hotel(hotel) for hotel in hotel_results[:5]]

        return {
            "hotel_results": hotel_results,
            "response_text": (
                f"I found {count} hotel option{'s' if count != 1 else ''}:\n"
                + "\n".join(lines)
            )
        }

    if flight_results:
        count = len(flight_results)
        lines = [_format_flight(flight) for flight in flight_results[:5]]

        return {
            "flight_results": flight_results,
            "response_text": (
                f"I found {count} flight option{'s' if count != 1 else ''}:\n"
                + "\n".join(lines)
            )
        }

    return {
        "hotel_results": [],
        "flight_results": [],
        "response_text": "I couldn't find matching travel options."
    }


def route_after_extraction(state: GraphState) -> str:
    intent = state.get("intent", "unknown")

    if intent == "hotel":
        return "hotel"

    if intent == "flight":
        return "flight"
        
    if intent == "plan":
        return "planner"

    if intent == "weather":
        return "weather"

    if intent == "transit":
        return "transit"

    return "unknown"