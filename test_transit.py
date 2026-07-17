import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.nodes import transit_node

async def test():
    state = {
        "origin": "London",
        "destination": "Paris",
        "city": "Paris",
        "messages": ["show transport options from London to Paris"]
    }
    print("Invoking transit_node...")
    result = await transit_node(state)
    print("SUCCESS! Result:")
    print(result)

if __name__ == "__main__":
    asyncio.run(test())
