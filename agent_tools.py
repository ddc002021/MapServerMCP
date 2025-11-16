from typing import Any, Dict
from servers.core_map_server import CoreMapServer, ServerParams as CoreServerParams
from servers.history_map_server import HistoryMapServer, ServerParams as HistoryServerParams
from servers.weather_map_server import WeatherEnvironmentServer, ServerParams as WeatherServerParams

# Initialize server instances
core_server = CoreMapServer(CoreServerParams())
history_server = HistoryMapServer(HistoryServerParams())
weather_server = WeatherEnvironmentServer(WeatherServerParams())

# Tool definitions following OpenAI function calling schema
TOOLS = [
    # Core Map Server Tools
    {
        "type": "function",
        "function": {
            "name": "geocode",
            "description": "Convert an address or place name to geographic coordinates (latitude and longitude) with a normalized address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The address or place name to geocode (e.g., 'Hamra Street, Beirut', '1600 Amphitheatre Parkway, Mountain View, CA')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reverse_geocode",
            "description": "Convert geographic coordinates (latitude and longitude) to a human-readable address with neighborhood information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude coordinate"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude coordinate"
                    }
                },
                "required": ["latitude", "longitude"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_poi",
            "description": "Find points of interest (POIs) near a location within a specified radius. Returns POI details including name, category, and distance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Center point latitude"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Center point longitude"
                    },
                    "radius": {
                        "type": "integer",
                        "description": "Search radius in meters (default: 1000)",
                        "default": 1000
                    },
                    "category": {
                        "type": "string",
                        "description": "POI category to search for. This should be an OpenStreetMap TAG KEY (e.g., 'amenity', 'shop', 'tourism')",
                        "default": "amenity"
                    },
                    "key": {
                        "type": "string",
                        "description": "Key to search for. This should be an OpenStreetMap TAG VALUE for the chosen category. This is the specific place type (cafe, supermarket, None etc.) (default: None)",
                        "default": None
                    }
                },
                "required": ["latitude", "longitude"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_place_details",
            "description": "Get detailed information about a specific place using its place ID. Returns name, full address, coordinates, contact info, and opening hours if available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place_id": {
                        "type": "string",
                        "description": "OpenStreetMap place ID (e.g., 'N123456' for node, 'W123456' for way) (Not the coordinates or the name of the place)"
                    }
                },
                "required": ["place_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_route",
            "description": "Calculate a route between two geographic coordinates. Returns distance, duration, turn-by-turn steps, and a summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin_lat": {
                        "type": "number",
                        "description": "Origin latitude"
                    },
                    "origin_lon": {
                        "type": "number",
                        "description": "Origin longitude"
                    },
                    "dest_lat": {
                        "type": "number",
                        "description": "Destination latitude"
                    },
                    "dest_lon": {
                        "type": "number",
                        "description": "Destination longitude"
                    },
                    "mode": {
                        "type": "string",
                        "description": "Transportation mode: 'driving', 'walking', or 'cycling'",
                        "enum": ["driving", "walking", "cycling"],
                        "default": "driving"
                    }
                },
                "required": ["origin_lat", "origin_lon", "dest_lat", "dest_lon"]
            }
        }
    },
    
    # History Map Server Tools
    {
        "type": "function",
        "function": {
            "name": "get_frequent_places",
            "description": "Retrieve frequently visited places from historical trip data within a specified time window. Returns places with visit counts. Note that the label is not the name of the place, it is a user set label.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (optional). If the user prompts for a certain period of time, explicitely keep asking for the start and end date until the user provides the date. Don't assume the start date no matter what."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (optional). If the user prompts for a certain period of time, explicitely keep asking for the start and end date until the user provides the date. Don't assume the end date no matter what."
                    },
                    "min_visits": {
                        "type": "integer",
                        "description": "Minimum number of visits to include a place (default: 3)",
                        "default": 3
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_travel_stats",
            "description": "Get aggregate travel statistics over a time period. Returns total trips, distance, time spent traveling, breakdown by transportation mode, and top routes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (optional)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (optional)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_typical_route",
            "description": "Get typical route characteristics between two frequently visited places. Returns average duration, distance, most common transportation mode, and trip count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin_label": {
                        "type": "string",
                        "description": "Origin place label (e.g., 'Home', 'Office')"
                    },
                    "destination_label": {
                        "type": "string",
                        "description": "Destination place label"
                    },
                    "time_of_day": {
                        "type": "integer",
                        "description": "Hour of day (0-23) to filter trips (optional)"
                    }
                },
                "required": ["origin_label", "destination_label"]
            }
        }
    },

    # Weather & Environment Server Tools
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get current weather conditions at a location including temperature, humidity, wind, and precipitation. Optionally includes 24-hour forecast.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude coordinate"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude coordinate"
                    },
                    "include_forecast": {
                        "type": "boolean",
                        "description": "Include 24-hour forecast (default: false)",
                        "default": False
                    }
                },
                "required": ["latitude", "longitude"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_air_quality",
            "description": "Get air quality index (AQI) and pollutant levels at a location. Returns health recommendations based on current air quality.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude coordinate"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude coordinate"
                    }
                },
                "required": ["latitude", "longitude"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_astronomy_data",
            "description": "Get astronomy data including sunrise, sunset, daylight hours, and moon phase for a location and date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude coordinate"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude coordinate"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (optional, defaults to today)"
                    }
                },
                "required": ["latitude", "longitude"]
            }
        }
    }
]


async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool by name with given arguments.
    Routes to appropriate MCP server method.
    """
    # Core Map Server tools
    if tool_name == "geocode":
        return await core_server.geocode(arguments["query"])
    
    elif tool_name == "reverse_geocode":
        return await core_server.reverse_geocode(
            arguments["latitude"],
            arguments["longitude"]
        )
    
    elif tool_name == "search_poi":
        return await core_server.search_poi(
            arguments["latitude"],
            arguments["longitude"],
            arguments.get("radius", 1000),
            arguments.get("category", "amenity"),
            arguments.get("key", None)
        )
    
    elif tool_name == "get_place_details":
        return await core_server.get_place_details(arguments["place_id"])
    
    elif tool_name == "get_route":
        return await core_server.get_route(
            arguments["origin_lat"],
            arguments["origin_lon"],
            arguments["dest_lat"],
            arguments["dest_lon"],
            arguments.get("mode", "driving")
        )
    
    # History Map Server tools
    elif tool_name == "get_frequent_places":
        return await history_server.get_frequent_places(
            arguments.get("start_date"),
            arguments.get("end_date"),
            arguments.get("min_visits", 3)
        )
    
    elif tool_name == "summarize_travel_stats":
        return await history_server.summarize_travel_stats(
            arguments.get("start_date"),
            arguments.get("end_date")
        )
    
    elif tool_name == "get_typical_route":
        return await history_server.get_typical_route(
            arguments["origin_label"],
            arguments["destination_label"],
            arguments.get("time_of_day")
        )

    # Weather & Environment Server tools
    elif tool_name == "get_current_weather":
        return await weather_server.get_current_weather(
            arguments["latitude"],
            arguments["longitude"],
            arguments.get("include_forecast", False)
        )
    
    elif tool_name == "get_air_quality":
        return await weather_server.get_air_quality(
            arguments["latitude"],
            arguments["longitude"]
        )
    
    elif tool_name == "get_astronomy_data":
        return await weather_server.get_astronomy_data(
            arguments["latitude"],
            arguments["longitude"],
            arguments.get("date")
        )
    
    else:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}"
        }


async def cleanup():
    """Cleanup server resources"""
    await core_server.close()
    await weather_server.close()