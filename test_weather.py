import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.nodes import weather_node

async def test():
    state = {
        "city": "Colombo",
        "flight_date": "2026-10-01",
        "messages": ["check weather in colombo"]
    }
    print("Invoking weather_node...")
    result = await weather_node(state)
    print("SUCCESS! Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(test())
