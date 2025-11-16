import httpx
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class ServerParams:
    """MCP Server Parameters for Core Map Server"""
    name: str = "core_map_server"
    description: str = "Provides geocoding, reverse geocoding, POI search, place details, and routing services"
    base_url_nominatim: str = "https://nominatim.openstreetmap.org"
    base_url_osrm: str = "https://router.project-osrm.org"
    base_url_overpass: str = "https://overpass-api.de/api/interpreter"
    user_agent: str = "MCP-Map-Agent/1.0"
    rate_limit_delay: float = float(os.getenv("API_RATE_LIMIT_DELAY"))


class CoreMapServer:
    """Core mapping operations server following MCP conventions"""
    
    def __init__(self, params: Optional[ServerParams] = None):
        self.params = params or ServerParams()
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def close(self):
        """Cleanup resources"""
        await self.client.aclose()
    
    async def geocode(self, query: str) -> Dict[str, Any]:
        """
        Convert address or place name to coordinates.
        
        Args:
            query: Address or place name to geocode
            
        Returns:
            Dictionary with lat, lon, display_name, and normalized address
        """
        await asyncio.sleep(self.params.rate_limit_delay)
        
        try:
            response = await self.client.get(
                f"{self.params.base_url_nominatim}/search",
                params={
                    "q": query,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1
                },
                headers={"User-Agent": self.params.user_agent}
            )
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return {
                    "success": False,
                    "error": f"No results found for '{query}'"
                }
            
            result = data[0]
            return {
                "success": True,
                "latitude": float(result["lat"]),
                "longitude": float(result["lon"]),
                "display_name": result["display_name"],
                "address": result.get("address", {}),
                "normalized_address": result["display_name"]
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Geocoding error: {str(e)}"
            }
    
    async def reverse_geocode(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Convert coordinates to human-readable address.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Dictionary with address components and neighborhood info
        """
        await asyncio.sleep(self.params.rate_limit_delay)
        
        try:
            response = await self.client.get(
                f"{self.params.base_url_nominatim}/reverse",
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "format": "json",
                    "addressdetails": 1
                },
                headers={"User-Agent": self.params.user_agent}
            )
            response.raise_for_status()
            data = response.json()
            
            address = data.get("address", {})
            return {
                "success": True,
                "display_name": data.get("display_name", ""),
                "address": {
                    "road": address.get("road", ""),
                    "neighbourhood": address.get("neighbourhood", address.get("suburb", "")),
                    "city": address.get("city", address.get("town", address.get("village", ""))),
                    "state": address.get("state", ""),
                    "country": address.get("country", ""),
                    "postcode": address.get("postcode", "")
                },
                "latitude": latitude,
                "longitude": longitude
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Reverse geocoding error: {str(e)}"
            }
    
    async def search_poi(self, latitude: float, longitude: float, radius: int = 1000, category: str = "amenity", key: Optional[str] = None) -> Dict[str, Any]:
        """
        Find points of interest near coordinates.
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius: Search radius in meters (default 1000)
            category: POI category (amenity, shop, tourism, etc.)
            key: Key to search for (cafe, supermarket, None etc.)
            
        Returns:
            List of POIs with id, name, category, distance
        """
        await asyncio.sleep(self.params.rate_limit_delay)
        
        try:
            # Overpass QL query
            query = f"""
            [out:json];
            (
              node["{category}"="{key}"](around:{radius},{latitude},{longitude});
              way["{category}"="{key}"](around:{radius},{latitude},{longitude});
            );
            out body;
            """
            
            response = await self.client.post(
                self.params.base_url_overpass,
                data={"data": query},
                headers={"User-Agent": self.params.user_agent}
            )
            response.raise_for_status()
            data = response.json()
           
            pois = []
            for element in data.get("elements", [])[:20]:  # Limit to 20 results
                tags = element.get("tags", {})
                poi_lat = element.get("lat", element.get("center", {}).get("lat", 0))
                poi_lon = element.get("lon", element.get("center", {}).get("lon", 0))
                
                # Calculate approximate distance
                distance = self._haversine_distance(
                    latitude, longitude, poi_lat, poi_lon
                )
                
                pois.append({
                    "id": element.get("id"),
                    "name": tags.get("name", "Unnamed"),
                    "category": category,
                    "key": tags.get(f"{category}", None),
                    "type": element.get("type"),
                    "distance_meters": round(distance, 2),
                    "latitude": poi_lat,
                    "longitude": poi_lon
                })
            
            return {
                "success": True,
                "count": len(pois),
                "pois": sorted(pois, key=lambda x: x["distance_meters"])
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"POI search error: {str(e)}"
            }
    
    async def get_place_details(self, place_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific place.
        
        Args:
            place_id: OSM place ID (format: N123456 for node, W123456 for way)
            
        Returns:
            Detailed place information
        """
        await asyncio.sleep(self.params.rate_limit_delay)
        
        try:
            # Determine type and ID
            if place_id.startswith('N'):
                osm_type = 'node'
                osm_id = place_id[1:]
            elif place_id.startswith('W'):
                osm_type = 'way'
                osm_id = place_id[1:]
            elif place_id.startswith('R'):
                osm_type = 'relation'
                osm_id = place_id[1:]
            else:
                osm_type = 'node'
                osm_id = place_id
            
            response = await self.client.get(
                f"{self.params.base_url_nominatim}/lookup",
                params={
                    "osm_ids": f"{osm_type[0].upper()}{osm_id}",
                    "format": "json",
                    "addressdetails": 1,
                    "extratags": 1
                },
                headers={"User-Agent": self.params.user_agent}
            )
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return {
                    "success": False,
                    "error": f"Place not found: {place_id}"
                }
            
            place = data[0]
            extratags = place.get("extratags", {})
            
            return {
                "success": True,
                "place_id": place_id,
                "name": place.get("display_name", "").split(",")[0],
                "full_address": place.get("display_name", ""),
                "latitude": float(place["lat"]),
                "longitude": float(place["lon"]),
                "address": place.get("address", {}),
                "category": place.get("class", ""),
                "type": place.get("type", ""),
                "phone": extratags.get("phone", extratags.get("contact:phone", "")),
                "website": extratags.get("website", extratags.get("contact:website", "")),
                "opening_hours": extratags.get("opening_hours", ""),
                "extratags": extratags
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Place details error: {str(e)}"
            }
    
    async def get_route(self, origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float, mode: str = "driving") -> Dict[str, Any]:
        """
        Get route between two points.
        
        Args:
            origin_lat: Origin latitude
            origin_lon: Origin longitude
            dest_lat: Destination latitude
            dest_lon: Destination longitude
            mode: Transport mode (driving, walking, cycling)
            
        Returns:
            Route with distance, duration, steps, and summary
        """
        await asyncio.sleep(self.params.rate_limit_delay)
        
        # Map modes to OSRM profiles
        mode_map = {
            "driving": "car",
            "walking": "foot",
            "cycling": "bike",
            "car": "car",
            "foot": "foot",
            "bike": "bike"
        }
        profile = mode_map.get(mode.lower(), "car")
        
        try:
            response = await self.client.get(
                f"{self.params.base_url_osrm}/route/v1/{profile}/{origin_lon},{origin_lat};{dest_lon},{dest_lat}",
                params={
                    "overview": "full",
                    "steps": "true",
                    "geometries": "geojson"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != "Ok":
                return {
                    "success": False,
                    "error": f"Routing error: {data.get('message', 'Unknown error')}"
                }
            
            route = data["routes"][0]
            legs = route["legs"][0]
            steps = legs.get("steps", [])
            
            # Extract step instructions
            instructions = []
            for step in steps[:10]:  # Limit to first 10 steps
                maneuver = step.get("maneuver", {})
                instructions.append({
                    "instruction": maneuver.get("instruction", "Continue"),
                    "distance_meters": round(step.get("distance", 0), 2),
                    "duration_seconds": round(step.get("duration", 0), 2)
                })
            
            return {
                "success": True,
                "mode": mode,
                "distance_meters": round(route.get("distance", 0), 2),
                "distance_km": round(route.get("distance", 0) / 1000, 2),
                "duration_seconds": round(route.get("duration", 0), 2),
                "duration_minutes": round(route.get("duration", 0) / 60, 2),
                "steps": instructions,
                "summary": f"{round(route.get('distance', 0) / 1000, 1)} km, approximately {round(route.get('duration', 0) / 60, 0)} minutes by {mode}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Routing error: {str(e)}"
            }
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371000  # Earth radius in meters
        
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)
        
        a = sin(delta_lat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c