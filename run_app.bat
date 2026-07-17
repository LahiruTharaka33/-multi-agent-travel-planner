@echo off
echo ==========================================
echo   TripWeaver Startup Helper (Windows)
echo ==========================================
echo.

echo [+] Starting Hotel MCP Service (Port 8001)...
start "hotel_service (8001)" cmd /k "python mcp_servers/hotel_service.py"

echo [+] Starting Flight MCP Service (Port 8002)...
start "flight_service (8002)" cmd /k "python mcp_servers/flight_service.py"

echo [+] Starting Weather MCP Service (Port 8004)...
start "weather_service (8004)" cmd /k "python mcp_servers/weather_service.py"

echo [+] Starting Transit MCP Service (Port 8005)...
start "transit_service (8005)" cmd /k "python mcp_servers/transit_service.py"

echo [+] Starting FastAPI Main Backend (Port 8003)...
start "tripweaver_backend (8003)" cmd /k "python main.py"

echo [+] Starting React Vite Frontend (Port 5173)...
start "tripweaver_frontend (5173)" cmd /k "cd frontend && npm run dev"

echo.
echo [!] Waiting 3 seconds for services to initialize...
timeout /t 3 /nobreak > nul

echo [+] Launching browser to http://localhost:5173 ...
start http://localhost:5173

echo.
echo ==========================================
echo   All 6 services launched! Check terminal
echo   windows for log outputs.
echo ==========================================
pause
