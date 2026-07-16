import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from langchain_mcp_adapters.tools import load_mcp_tools
load_dotenv()

HOTEL_MCP_URL = os.getenv("HOTEL_MCP_URL", "http://localhost:8001/mcp")
FLIGHT_MCP_URL = os.getenv("FLIGHT_MCP_URL", "http://localhost:8002/mcp")


#HOTEL_MCP_URL = "http://localhost:8001/mcp"
#FLIGHT_MCP_URL = "http://localhost:8002/mcp"




@asynccontextmanager
async def hotel_mcp_tools():
    """Async context manager that yields hotel tools with an active MCP session."""
    async with streamablehttp_client(HOTEL_MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            yield {tool.name: tool for tool in tools}


@asynccontextmanager
async def flight_mcp_tools():
    """Async context manager that yields flight tools with an active MCP session."""
    async with streamablehttp_client(FLIGHT_MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            yield {tool.name: tool for tool in tools}
