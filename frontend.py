import json
import os
import requests
#from urllib.request import Request, urlopen
import gradio as gr
from dotenv import load_dotenv

load_dotenv()



def format_flights(flights):
    lines = ["Flights:"]
    for flight in flights:
        #id = flight.get("_id", "Unknown ID")
        airline = flight.get("airline", "Unknown Airline")
        flight_number = flight.get("flightNumber", "Unknown Flight Number")
        origin = flight.get("origin", {}).get("airport", "Unknown Origin")
        destination = flight.get("destination", {}).get("airport", "Unknown Destination")
        flight_date = flight.get("flightDate", "Unknown Date")
        departure_time = flight.get("departureTime", "Unknown Departure Time")
        arrival_time = flight.get("arrivalTime", "Unknown Arrival Time")
        #price = flight.get("price", "Unknown Price")
        #currency = flight.get("currency", "Unknown Currency")
        available_seats = flight.get("availableSeats", "Unknown Available Seats")
        lines.append(
            f"{airline} {flight_number} from {origin} to {destination} "
            f"on {flight_date} {departure_time} - {arrival_time} "
            f"- {available_seats} seats"
        )
    return "\n".join(lines)


def format_hotels(hotels):
    lines = ["Hotels:"]
    for hotel in hotels:
        #id = hotel.get("_id", "Unknown ID")
        name = hotel.get("name") or "Unknown Hotel"
        city = hotel.get("city") or hotel.get("location", {}).get("city", "")
        #price_per_night = hotel.get("pricePerNight") or "Price not available"
        #currency = hotel.get("price") or hotel.get("currency", "")
        lines.append(f"{name} in {city} ")
    return "\n".join(lines)


def call_chat_api(message):
    url = os.getenv("BACKEND_STREAM_URL")
    payload = {"message":message}

    status_lines = []
    final_answer = ""

    try:
        response = requests.post(url, json=payload, stream=True, timeout=30)
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if chunk["type"] == "status":
                    status_lines.append(chunk["content"])
                elif chunk["type"] == "result":
                    final_answer = chunk["content"]
    except Exception as exc:
        return f"Error: {exc}"
    
    parts = status_lines + [final_answer]
    return "\n".join(parts)




def call_chat_api_stream(message):
    url = os.getenv("BACKEND_STREAM_URL")
    payload = {"message":message}
    try:
        response = requests.post(url, json=payload, stream=True, timeout=30)
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                yield chunk
    except Exception as exc:
        yield {"type": "error", "content": str(exc)}

def respond(message, history):
    if history is None:
        history = []
    
    partial = ""
    status_log = []
    
    for chunk in call_chat_api_stream(message):
        chunk_type = chunk.get("type")
        content = chunk.get("content", "")

        if chunk_type == "status":
           status_log.append(content)
           current_display = "\n".join(status_log) + "\n ⏳ Working..."
           yield (
                history + [{"role": "user", "content": message},
                            {"role": "assistant", "content": current_display}],
                history
           )
           
        elif chunk_type == "result":
            partial = "\n".join(status_log) + "\n\n" + content
            yield (
                history + [{"role": "user", "content": message},
                            {"role": "assistant", "content": partial}],
                history + [{"role": "user", "content": message},
                            {"role": "assistant", "content": partial}]
            )
        elif chunk_type == "error":
            yield (
                history + [{"role": "user", "content": message},
                            {"role": "assistant", "content": f"⚠️ {content}"}],
                history
            )
            
    


def main():
    with gr.Blocks() as demo:
        gr.Markdown(
            "# Travel Planner Chat\nAsk the backend for flights, hotels, or travel plans. ``TRAVEL_PLANNER_API_URL`` can be set to point to your FastAPI server."
        )
        chatbot = gr.Chatbot(type="messages")
        message = gr.Textbox(label="Your message", placeholder="Find me flights from CAN to HAN on 2025-11-15")
        submit = gr.Button("Send")

        submit.click(respond, inputs=[message, chatbot], outputs=[chatbot, chatbot])
        message.submit(respond, inputs=[message, chatbot], outputs=[chatbot, chatbot])

    demo.launch()


if __name__ == "__main__":
    main()