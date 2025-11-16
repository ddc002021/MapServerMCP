import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class ServerParams:
    """MCP Server Parameters for History Map Server"""
    name: str = "history_map_server"
    description: str = "Provides historical travel pattern analysis and statistics"
    data_file: str = "data/trip_history.json"


class HistoryMapServer:
    """Historical travel data analysis server following MCP conventions"""
    
    def __init__(self, params: Optional[ServerParams] = None):
        self.params = params or ServerParams()
        self.trip_data = self._load_trip_data()
    
    def _load_trip_data(self) -> List[Dict[str, Any]]:
        """Load trip history data from file or generate sample data"""
        with open(self.params.data_file, 'r') as f:
            return json.load(f)
    
    async def get_frequent_places(self, start_date: Optional[str] = None, end_date: Optional[str] = None, min_visits: int = 3) -> Dict[str, Any]:
        """
        Get frequently visited places from historical trips.
        
        Args:
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            min_visits: Minimum visit count to include
            
        Returns:
            List of frequent places with visit counts
        """
        try:
            # Filter trips by date range
            filtered_trips = self.trip_data
            
            if start_date:
                filtered_trips = [t for t in filtered_trips if t["date"] >= start_date]
            if end_date:
                filtered_trips = [t for t in filtered_trips if t["date"] <= end_date]
            
            # Count visits to each place
            place_visits = defaultdict(lambda: {"count": 0, "coords": None, "label": None})
            
            for trip in filtered_trips:
                # Count origin
                origin_key = f"{trip['origin']['lat']},{trip['origin']['lon']}"
                place_visits[origin_key]["count"] += 1
                place_visits[origin_key]["coords"] = (trip['origin']['lat'], trip['origin']['lon'])
                place_visits[origin_key]["label"] = trip['origin']['label']
                
                # Count destination
                dest_key = f"{trip['destination']['lat']},{trip['destination']['lon']}"
                place_visits[dest_key]["count"] += 1
                place_visits[dest_key]["coords"] = (trip['destination']['lat'], trip['destination']['lon'])
                place_visits[dest_key]["label"] = trip['destination']['label']
            
            # Filter by minimum visits
            frequent_places = [
                {
                    "label": data["label"],
                    "latitude": data["coords"][0],
                    "longitude": data["coords"][1],
                    "visit_count": data["count"]
                }
                for data in place_visits.values()
                if data["count"] >= min_visits
            ]
            
            frequent_places.sort(key=lambda x: x["visit_count"], reverse=True)
            
            return {
                "success": True,
                "time_window": {
                    "start_date": start_date or filtered_trips[-1]["date"] if filtered_trips else None,
                    "end_date": end_date or filtered_trips[0]["date"] if filtered_trips else None
                },
                "total_places": len(frequent_places),
                "places": frequent_places
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting frequent places: {str(e)}"
            }
    
    async def summarize_travel_stats(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get aggregate travel statistics over a time window.
        
        Args:
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            
        Returns:
            Aggregate statistics including trips, distance, time by mode
        """
        try:
            # Filter trips by date range
            filtered_trips = self.trip_data
            
            if start_date:
                filtered_trips = [t for t in filtered_trips if t["date"] >= start_date]
            if end_date:
                filtered_trips = [t for t in filtered_trips if t["date"] <= end_date]
            
            if not filtered_trips:
                return {
                    "success": False,
                    "error": "No trips found in specified time window"
                }
            
            # Calculate statistics
            total_trips = len(filtered_trips)
            total_distance = sum(t["distance_km"] for t in filtered_trips)
            total_time = sum(t["duration_minutes"] for t in filtered_trips)
            
            # Stats by mode
            mode_stats = defaultdict(lambda: {"trips": 0, "distance_km": 0, "time_minutes": 0})
            for trip in filtered_trips:
                mode = trip["mode"]
                mode_stats[mode]["trips"] += 1
                mode_stats[mode]["distance_km"] += trip["distance_km"]
                mode_stats[mode]["time_minutes"] += trip["duration_minutes"]
            
            # Top routes
            route_counts = defaultdict(int)
            for trip in filtered_trips:
                route_key = f"{trip['origin']['label']} → {trip['destination']['label']}"
                route_counts[route_key] += 1
            
            top_routes = sorted(
                [{"route": k, "trip_count": v} for k, v in route_counts.items()],
                key=lambda x: x["trip_count"],
                reverse=True
            )[:5]
            
            return {
                "success": True,
                "time_window": {
                    "start_date": start_date or filtered_trips[-1]["date"],
                    "end_date": end_date or filtered_trips[0]["date"]
                },
                "summary": {
                    "total_trips": total_trips,
                    "total_distance_km": round(total_distance, 2),
                    "total_time_hours": round(total_time / 60, 2),
                    "avg_trip_distance_km": round(total_distance / total_trips, 2),
                    "avg_trip_duration_minutes": round(total_time / total_trips, 2)
                },
                "by_mode": dict(mode_stats),
                "top_routes": top_routes
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error summarizing travel stats: {str(e)}"
            }
    
    async def get_typical_route(self, origin_label: str, destination_label: str, time_of_day: Optional[int] = None) -> Dict[str, Any]:
        """
        Get typical route characteristics between two frequent places.
        
        Args:
            origin_label: Origin place label
            destination_label: Destination place label
            time_of_day: Hour of day (0-23) for filtering
            
        Returns:
            Average duration, distance, mode, and trip count
        """
        try:
            # Filter trips matching the route
            matching_trips = [
                t for t in self.trip_data
                if t["origin"]["label"] == origin_label 
                and t["destination"]["label"] == destination_label
            ]
            
            if time_of_day is not None:
                matching_trips = [
                    t for t in matching_trips
                    if t["hour"] == time_of_day
                ]
            
            if not matching_trips:
                return {
                    "success": False,
                    "error": f"No trips found for route {origin_label} → {destination_label}"
                }
            
            # Calculate averages
            avg_distance = sum(t["distance_km"] for t in matching_trips) / len(matching_trips)
            avg_duration = sum(t["duration_minutes"] for t in matching_trips) / len(matching_trips)
            
            # Most common mode
            mode_counts = defaultdict(int)
            for trip in matching_trips:
                mode_counts[trip["mode"]] += 1
            most_common_mode = max(mode_counts.items(), key=lambda x: x[1])[0]
            
            return {
                "success": True,
                "route": f"{origin_label} → {destination_label}",
                "time_of_day_filter": time_of_day,
                "trip_count": len(matching_trips),
                "average_distance_km": round(avg_distance, 2),
                "average_duration_minutes": round(avg_duration, 2),
                "most_common_mode": most_common_mode,
                "mode_distribution": dict(mode_counts)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting typical route: {str(e)}"
            }