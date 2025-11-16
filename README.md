Dany Chahine - 202107582

EECE798S - Assignment 5

# MCP Map Servers with OpenAI Agents SDK

Implementation of three Model Context Protocol (MCP) servers providing mapping, travel analysis, and weather/environment services using the OpenAI Agents SDK.

---

## 🎯 Project Overview

This project implements **three MCP servers** with **11 total operations** as agent tools:

| Server | Operations | Description |
|--------|-----------|-------------|
| **Core Map Server** | 5 | Real-time geocoding, POI search, routing |
| **History Map Server** | 3 | Historical travel pattern analysis |
| **Weather & Environment Server** | 3 | Weather, air quality, astronomy data |

---

## 🚀 Quick Start

### 1. Installation (3 minutes)

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # macOS/Linux
venv\Scripts\activate              # Windows

# Install dependencies
pip install -r requirements.txt

# Configure OpenAI API key
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-your-key-here
```
**Note:** Set the `verbose` parameter in `agent.py` to "True" in order to print the tool calls that agent makes before answering.

### 2. Run the project

**Interactive Agent (With example queries):**
```bash
python agent.py
```

**Run Tests:**
```bash
pytest tests/ -v
```

---

## 🎯 MCP Architecture

This implementation follows Model Context Protocol conventions:

1. **ServerParams** - Configuration for each server
2. **Async Operations** - All I/O is non-blocking
3. **Structured Responses** - Consistent `{success, ...}` format
4. **Tool Definitions** - OpenAI function calling schema
5. **Resource Management** - Proper cleanup with `close()`

### Tool Flow

```
User Query
    ↓
OpenAI Agent (decides which tools to use)
    ↓
Tool Execution (agent_tools.py routes to server)
    ↓
MCP Server Method (performs operation)
    ↓
External API Call
    ↓
Structured Response
    ↓
Agent Formats Response for User
```

---

## 📚 Server Details

### Core Map Server (`servers/core_map_server.py`)

Real-time mapping using OpenStreetMap APIs.

**Operations:**
- `geocode(query)` - Get coordinates from an address
- `reverse_geocode(lat, lon)` - Get address from coordinates 
- `search_poi(lat, lon, radius, category, key)` - Find nearby places
- `get_place_details(place_id)` - Detailed place information
- `get_route(origin_lat, origin_lon, dest_lat, dest_lon, mode)` - Calculate routes

**External APIs:** Nominatim, OSRM, Overpass

### History Map Server (`servers/history_map_server.py`)

Travel pattern analysis using historical trip data.

**Operations:**
- `get_frequent_places(start_date, end_date, min_visits)` - Most visited locations
- `summarize_travel_stats(start_date, end_date)` - Aggregate travel statistics
- `get_typical_route(origin_label, dest_label, time_of_day)` - Route patterns

**Data:** Uses 100 generated trips found in `data/trip_history.json`

### Weather & Environment Server (`servers/weather_environment_server.py`)

Weather and environmental data for any location.

**Operations:**
- `get_current_weather(lat, lon, include_forecast)` - Temperature, conditions, wind
- `get_air_quality(lat, lon)` - AQI, pollutants, health recommendations  
- `get_astronomy_data(lat, lon, date)` - Sunrise, sunset, moon phase

**External API:** Open-Meteo

---

## 💡 Example Usage

```python
python agent.py

💬 You: What's the weather in Paris?
🤖 Agent: [Uses geocode + get_current_weather tools]

💬 You: Find coffee shops near Times Square
🤖 Agent: [Uses geocode + search_poi tools]

💬 You: How's the air quality in Beijing?
🤖 Agent: [Uses geocode + get_air_quality tools]

💬 You: Route from Central Park to Brooklyn Bridge by walking
🤖 Agent: [Uses geocode + get_route tools]

💬 You: What are my travel statistics?
🤖 Agent: [Uses summarize_travel_stats tool]
```

---

## 🗂️ Project Structure

```
mcp-map-servers/
├── agent.py                         # Main interactive agent
├── agent_tools.py                   # Tool definitions & routing
├── agent_prompt.txt                 # The agent prompt
├── servers/
│   ├── core_map_server.py           # Geocoding, POI, routing
│   ├── history_map_server.py        # Travel pattern analysis
│   └── weather_map_server.py        # Weather & environment
├── tests/
│   └── test_servers.py              # Unit tests
├── data/
│   └── trip_history.json            # Generated data
├── requirements.txt
├── .env.example
└── README.md                        # This file
└── REFLECTION.md                    # Lessons learned and potential next steps
└── SUMMARY.md                       # Summary of the huggingface MCP article and existing map servers
└── Screencast.mp4                   # Video showcasing examples and explaining implementation
```

---

## 🧪 Testing

Run all tests:
```bash
pytest tests/ -v
```

Run specific test:
```bash
pytest tests/test_servers.py::TestCoreMapServer::test_geocode_success -v
```

Tests cover:
- All 11 server operations
- Success and error cases
- Real API integrations
- Data structure validation

---

## ⚙️ Configuration

### Environment Variables (`.env`)

```bash
OPENAI_API_KEY=sk-your-key-here
API_RATE_LIMIT_DELAY=1.0
OPENAI_MODEL="gpt-4o"
```

### Server Parameters

Each server uses a `ServerParams` dataclass for configuration:

```python
@dataclass
class ServerParams:
    name: str = "server_name"
    description: str = "Server description"
    base_url: str = "https://api.example.com"
    rate_limit_delay: float = float(os.getenv("API_RATE_LIMIT_DELAY"))
```

---

## 🌐 External APIs

| API | Purpose | Key Required | Rate Limit |
|-----|---------|--------------|------------|
| Nominatim | Geocoding | No | 1 req/sec |
| OSRM | Routing | No | Fair use |
| Overpass | POI Search | No | Fair use |
| Open-Meteo | Weather & Air Quality | No | Fair use |

All APIs are **free** and **require no authentication**.

---

## 🔐 Error Handling

All operations return consistent structure:

**Success:**
```python
{
    "success": True,
    "data": "...",
    # ... other fields
}
```

**Failure:**
```python
{
    "success": False,
    "error": "Descriptive error message"
}
```

This allows the agent to:
1. Check operation success
2. Extract data or report errors appropriately
3. Handle failures gracefully

---

## 🚧 Extending the System

### Add a New Tool to Existing Server

1. Add method to server class in `servers/`
2. Add tool definition to `TOOLS` in `agent_tools.py`
3. Add routing case to `execute_tool()` in `agent_tools.py`
4. Optional: Write tests in `tests/test_servers.py`

### Create a New Server

1. Create `servers/new_server.py` with `ServerParams` and server class
2. Import and initialize in `agent_tools.py`
3. Add tool definitions to `TOOLS` list
4. Add routing cases to `execute_tool()`
5. Update system prompt in `agent.py`
6. Optional: Write tests

---

## Assignment Deliverables

1. SUMMARY.md (Summary of the huggingface MCP article and existing map servers)
2. REFLECTION.md (Lessons learned and potential next steps)
3. Screencast: 
https://github.com/user-attachments/assets/a032c84c-b936-4008-a52b-57ab35f456a4
