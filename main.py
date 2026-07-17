from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
#from agents.tools import get_hotels, get_flights
from entity import ChatRequest, ChatResponse
from agents.graph import graph
import json
import logging
from fastapi.responses import StreamingResponse


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("api")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def greeting():
    return {"message": "Welcome to the Multi-Agent Travel Planner API"}

# @app.get("/hotels")
# async def hotels():
#     return get_hotels.invoke({})

# @app.get("/flights")
# async def flights():
#     return get_flights.invoke({})


conversation_history_messages = []

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):

    recent_pairs = conversation_history_messages[-3:]
    flattened_messages = []
    for user_msg, assistant_msg in recent_pairs:
        flattened_messages.append(user_msg)
        flattened_messages.append(assistant_msg)
    flattened_messages.append(request.message)

    initial_state = {
        "messages": flattened_messages,
    }

    config = {"configurable": {"thread_id": request.session_id}}

    result =await graph.ainvoke(initial_state, config=config)

    response_text = result.get("response_text", "Something went wrong. Please try again.")

    conversation_history_messages.append((request.message, response_text))


    return ChatResponse(
        response=result.get("response_text", "Something went wrong. Please try again."),
        hotels=result.get("hotel_results", []) or None,
        flights=result.get("flight_results", []) or None,
        weather=result.get("weather_results", []) or None,
        transit=result.get("transit_results", []) or None,
    )

async def stream_graph_events(initial_state, session_id: str = "default"):
    final_result = None
    config = {"configurable": {"thread_id": session_id}}

    final_result = ""
    structured_hotels = []
    structured_flights = []
    structured_weather = []
    structured_transit = []

    async for event in graph.astream_events(initial_state, config=config, version="v2"):

        event_type = event["event"]
        node_name = event.get("name", "")

        if event_type == "on_chain_end" and node_name in ("hotel_node","flight_node","weather_node","transit_node","planner_node","router"):
            yield json.dumps({"type":"status","content": f"processing {node_name} completed..."})+"\n"
        
        if event_type == "on_chain_end" and node_name == "generate_response":
            output = event.get("data", {}).get("output",{})
            final_result = output.get("response_text","")
            structured_hotels = output.get("hotel_results", [])
            structured_flights = output.get("flight_results", [])
            structured_weather = output.get("weather_results", [])
            structured_transit = output.get("transit_results", [])
    
    if final_result:
        yield json.dumps({"type":"result", "content":final_result})+"\n"
        yield json.dumps({
            "type": "structured_data", 
            "hotels": structured_hotels, 
            "flights": structured_flights,
            "weather": structured_weather,
            "transit": structured_transit
        })+"\n"
    else:
        yield json.dumps ({"type":"result", "content":"Something went wrong. Please try again."})+"\n" 


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):

    recent_pairs = conversation_history_messages[-3:]
    flattened_messages = []
    for user_msg, assistant_msg in recent_pairs:
        flattened_messages.append(user_msg)
        flattened_messages.append(assistant_msg)
    flattened_messages.append(request.message)

    initial_state = {
        "messages": flattened_messages,
    }


    return StreamingResponse(
        stream_graph_events(initial_state, session_id=request.session_id),
        media_type="text/event-stream"
    )
    

            

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

# Run the app: uvicorn main:app --reload