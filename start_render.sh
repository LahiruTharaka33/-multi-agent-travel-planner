#!/bin/bash

# Start the MCP servers in the background
echo "Starting Hotel MCP..."
python mcp_servers/hotel_service.py &

echo "Starting Flight MCP..."
python mcp_servers/flight_service.py &

echo "Starting Weather MCP..."
python mcp_servers/weather_service.py &

echo "Starting Transit MCP..."
python mcp_servers/transit_service.py &

# Wait a few seconds to let MCP servers initialize
sleep 3

# Start the main FastAPI backend on the port Render gives us (defaults to 10000 or 8000)
# We fall back to 8003 if PORT is not set.
PORT="${PORT:-8003}"
echo "Starting FastAPI on port $PORT..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT
