import pytest
import asyncio
from servers.core_map_server import CoreMapServer, ServerParams as CoreServerParams
from servers.history_map_server import HistoryMapServer, ServerParams as HistoryServerParams
from servers.weather_map_server import WeatherEnvironmentServer, ServerParams as WeatherServerParams

@pytest.mark.asyncio
class TestCoreMapServer:
    """Tests for Core Map Server"""
    
    async def test_geocode_success(self):
        """Test successful geocoding"""
        server = CoreMapServer(CoreServerParams())
        result = await server.geocode("Eiffel Tower, Paris")
        
        assert result["success"] is True
        assert "latitude" in result
        assert "longitude" in result
        assert "normalized_address" in result
        
        # Eiffel Tower should be around these coordinates
        assert 48.8 < result["latitude"] < 48.9
        assert 2.2 < result["longitude"] < 2.4
        
        await server.close()
    
    async def test_geocode_not_found(self):
        """Test geocoding with invalid address"""
        server = CoreMapServer(CoreServerParams())
        result = await server.geocode("XYZ123NonexistentPlace456")
        
        assert result["success"] is False
        assert "error" in result
        
        await server.close()
    
    async def test_reverse_geocode(self):
        """Test reverse geocoding"""
        server = CoreMapServer(CoreServerParams())
        # Coordinates for Times Square, NYC
        result = await server.reverse_geocode(40.7580, -73.9855)
        
        assert result["success"] is True
        assert "display_name" in result
        assert "address" in result
        assert result["latitude"] == 40.7580
        assert result["longitude"] == -73.9855
        
        await server.close()
    
    async def test_search_poi(self):
        """Test POI search"""
        server = CoreMapServer(CoreServerParams())
        # Search near Central Park, NYC
        result = await server.search_poi(33.899196542554186, 35.48135206349168, radius=500, category="amenity", key="cafe")
        
        assert result["success"] is True
        assert "pois" in result
        assert "count" in result
        assert isinstance(result["pois"], list)
        
        await server.close()
    
    async def test_get_route(self):
        """Test route calculation"""
        server = CoreMapServer(CoreServerParams())
        # Route from Central Park to Times Square
        result = await server.get_route(
            origin_lat=40.7829,
            origin_lon=-73.9654,
            dest_lat=40.7580,
            dest_lon=-73.9855,
            mode="driving"
        )
        
        assert result["success"] is True
        assert "distance_km" in result
        assert "duration_minutes" in result
        assert "steps" in result
        assert "summary" in result
        assert result["distance_km"] > 0
        
        await server.close()


@pytest.mark.asyncio
class TestHistoryMapServer:
    """Tests for History Map Server"""
    
    async def test_get_frequent_places(self):
        """Test getting frequent places"""
        server = HistoryMapServer(HistoryServerParams())
        result = await server.get_frequent_places(min_visits=2)
        
        assert result["success"] is True
        assert "places" in result
        assert "total_places" in result
        assert isinstance(result["places"], list)
        
        # Check structure of place data
        if result["places"]:
            place = result["places"][0]
            assert "label" in place
            assert "latitude" in place
            assert "longitude" in place
            assert "visit_count" in place
    
    async def test_summarize_travel_stats(self):
        """Test travel statistics summary"""
        server = HistoryMapServer(HistoryServerParams())
        result = await server.summarize_travel_stats()
        
        assert result["success"] is True
        assert "summary" in result
        assert "by_mode" in result
        assert "top_routes" in result
        
        summary = result["summary"]
        assert "total_trips" in summary
        assert "total_distance_km" in summary
        assert "total_time_hours" in summary
    
    async def test_get_typical_route(self):
        """Test typical route analysis"""
        server = HistoryMapServer(HistoryServerParams())
        
        # First get frequent places to find valid labels
        places_result = await server.get_frequent_places(min_visits=2)
        
        if len(places_result["places"]) >= 2:
            origin = places_result["places"][0]["label"]
            destination = places_result["places"][1]["label"]
            
            result = await server.get_typical_route(origin, destination)
            
            assert result["success"] is True
            assert "average_distance_km" in result
            assert "average_duration_minutes" in result
            assert "most_common_mode" in result
            assert "trip_count" in result
    
    async def test_get_typical_route_not_found(self):
        """Test typical route with non-existent places"""
        server = HistoryMapServer(HistoryServerParams())
        result = await server.get_typical_route("NonexistentPlace1", "NonexistentPlace2")
        
        assert result["success"] is False
        assert "error" in result

@pytest.mark.asyncio
class TestWeatherEnvironmentServer:
    """Tests for Weather & Environment Server"""
    
    async def test_get_current_weather(self):
        """Test getting current weather"""
        server = WeatherEnvironmentServer(WeatherServerParams())
        # Test for New York City
        result = await server.get_current_weather(40.7128, -74.0060)
        
        assert result["success"] is True
        assert "current" in result
        assert "temperature_f" in result["current"]
        assert "conditions" in result["current"]
        assert "summary" in result
        
        await server.close()
    
    async def test_get_current_weather_with_forecast(self):
        """Test weather with forecast"""
        server = WeatherEnvironmentServer(WeatherServerParams())
        result = await server.get_current_weather(40.7128, -74.0060, include_forecast=True)
        
        assert result["success"] is True
        assert "forecast_24h" in result
        assert len(result["forecast_24h"]) > 0
        
        await server.close()
    
    async def test_get_air_quality(self):
        """Test air quality data"""
        server = WeatherEnvironmentServer(WeatherServerParams())
        result = await server.get_air_quality(40.7128, -74.0060)
        
        assert result["success"] is True
        assert "air_quality" in result
        assert "us_aqi" in result["air_quality"]
        assert "category" in result["air_quality"]
        assert "pollutants" in result
        
        await server.close()
    
    async def test_get_astronomy_data(self):
        """Test astronomy data"""
        server = WeatherEnvironmentServer(WeatherServerParams())
        result = await server.get_astronomy_data(40.7128, -74.0060)
        
        assert result["success"] is True
        assert "sun" in result
        assert "sunrise" in result["sun"]
        assert "sunset" in result["sun"]
        assert "moon" in result
        assert "phase" in result["moon"]
        
        await server.close()
    
    async def test_get_astronomy_data_specific_date(self):
        """Test astronomy data for specific date"""
        server = WeatherEnvironmentServer(WeatherServerParams())
        result = await server.get_astronomy_data(40.7128, -74.0060, date="2025-11-16")
        
        assert result["success"] is True
        assert result["date"] == "2025-11-16"
        
        await server.close()

@pytest.mark.asyncio
async def test_server_params():
    """Test server parameter initialization"""
    core_params = CoreServerParams()
    assert core_params.name == "core_map_server"
    assert "nominatim" in core_params.base_url_nominatim
    
    history_params = HistoryServerParams()
    assert history_params.name == "history_map_server"

    weather_params = WeatherServerParams()
    assert weather_params.name == "weather_environment_server"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])