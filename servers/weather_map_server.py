import httpx
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ServerParams:
    """MCP Server Parameters for Weather & Environment Server"""
    name: str = "weather_environment_server"
    description: str = "Provides weather, air quality, and astronomy data for geographic locations"
    base_url_weather: str = "https://api.open-meteo.com/v1/forecast"
    base_url_air_quality: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    rate_limit_delay: float = 0.5


class WeatherEnvironmentServer:
    """Weather and environmental data server following MCP conventions"""
    
    def __init__(self, params: Optional[ServerParams] = None):
        self.params = params or ServerParams()
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def close(self):
        """Cleanup resources"""
        await self.client.aclose()
    
    async def get_current_weather(
        self, 
        latitude: float, 
        longitude: float,
        include_forecast: bool = False
    ) -> Dict[str, Any]:
        """
        Get current weather conditions at a location.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            include_forecast: If True, include 24-hour forecast
            
        Returns:
            Dictionary with temperature, conditions, wind, humidity, etc.
        """
        await asyncio.sleep(self.params.rate_limit_delay)
        
        try:
            # Build parameters
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph"
            }
            
            if include_forecast:
                params["hourly"] = "temperature_2m,precipitation_probability,weather_code"
                params["forecast_days"] = 1
            
            response = await self.client.get(
                self.params.base_url_weather,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            current = data.get("current", {})
            
            # Map weather codes to descriptions
            weather_desc = self._get_weather_description(current.get("weather_code", 0))
            
            result = {
                "success": True,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "timestamp": current.get("time", datetime.now(timezone.utc).isoformat()),
                "current": {
                    "temperature_f": current.get("temperature_2m"),
                    "feels_like_f": current.get("apparent_temperature"),
                    "humidity_percent": current.get("relative_humidity_2m"),
                    "precipitation_mm": current.get("precipitation"),
                    "wind_speed_mph": current.get("wind_speed_10m"),
                    "wind_direction_degrees": current.get("wind_direction_10m"),
                    "conditions": weather_desc
                },
                "summary": f"{weather_desc}, {current.get('temperature_2m', 'N/A')}°F (feels like {current.get('apparent_temperature', 'N/A')}°F)"
            }
            
            # Add forecast if requested
            if include_forecast and "hourly" in data:
                hourly = data["hourly"]
                forecast = []
                for i in range(min(24, len(hourly.get("time", [])))):
                    forecast.append({
                        "time": hourly["time"][i],
                        "temperature_f": hourly["temperature_2m"][i],
                        "precipitation_probability": hourly.get("precipitation_probability", [0])[i] if i < len(hourly.get("precipitation_probability", [])) else 0,
                        "conditions": self._get_weather_description(hourly["weather_code"][i])
                    })
                result["forecast_24h"] = forecast
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Weather data error: {str(e)}"
            }
    
    async def get_air_quality(
        self, 
        latitude: float, 
        longitude: float
    ) -> Dict[str, Any]:
        """
        Get air quality index and pollutant levels.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Dictionary with AQI, pollutant concentrations, and health recommendations
        """
        await asyncio.sleep(self.params.rate_limit_delay)
        
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone,us_aqi,european_aqi"
            }
            
            response = await self.client.get(
                self.params.base_url_air_quality,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            current = data.get("current", {})
            us_aqi = current.get("us_aqi", 0)
            
            # Determine AQI category and health recommendation
            aqi_category = self._get_aqi_category(us_aqi)
            
            return {
                "success": True,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "timestamp": current.get("time", datetime.now(timezone.utc).isoformat()),
                "air_quality": {
                    "us_aqi": us_aqi,
                    "european_aqi": current.get("european_aqi"),
                    "category": aqi_category["category"],
                    "health_impact": aqi_category["health_impact"],
                    "recommendation": aqi_category["recommendation"]
                },
                "pollutants": {
                    "pm2_5_ugm3": current.get("pm2_5", 0),
                    "pm10_ugm3": current.get("pm10", 0),
                    "carbon_monoxide_ugm3": current.get("carbon_monoxide", 0),
                    "nitrogen_dioxide_ugm3": current.get("nitrogen_dioxide", 0),
                    "ozone_ugm3": current.get("ozone", 0)
                },
                "summary": f"Air Quality: {aqi_category['category']} (AQI {us_aqi}) - {aqi_category['health_impact']}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Air quality data error: {str(e)}"
            }
    
    async def get_astronomy_data(
        self, 
        latitude: float, 
        longitude: float,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get astronomy data (sunrise, sunset, daylight hours, moon phase).
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            date: Date in YYYY-MM-DD format (default: today)
            
        Returns:
            Dictionary with sunrise, sunset, daylight duration, and moon phase
        """
        await asyncio.sleep(self.params.rate_limit_delay)
        
        try:
            # If no date provided, use today
            if not date:
                date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "daily": "sunrise,sunset,daylight_duration,sunshine_duration",
                "timezone": "auto",
                "start_date": date,
                "end_date": date
            }
            
            response = await self.client.get(
                self.params.base_url_weather,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            daily = data.get("daily", {})
            
            # Calculate moon phase (simplified)
            moon_phase = self._calculate_moon_phase(date)
            
            sunrise = daily.get("sunrise", ["N/A"])[0]
            sunset = daily.get("sunset", ["N/A"])[0]
            daylight_seconds = daily.get("daylight_duration", [0])[0]
            sunshine_seconds = daily.get("sunshine_duration", [0])[0]
            
            # Convert to hours
            daylight_hours = round(daylight_seconds / 3600, 2) if daylight_seconds else 0
            sunshine_hours = round(sunshine_seconds / 3600, 2) if sunshine_seconds else 0
            
            return {
                "success": True,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "date": date,
                "sun": {
                    "sunrise": sunrise,
                    "sunset": sunset,
                    "daylight_hours": daylight_hours,
                    "sunshine_hours": sunshine_hours
                },
                "moon": {
                    "phase": moon_phase["name"],
                    "illumination_percent": moon_phase["illumination"],
                    "emoji": moon_phase["emoji"]
                },
                "summary": f"Sunrise: {sunrise}, Sunset: {sunset} ({daylight_hours}h daylight). Moon: {moon_phase['emoji']} {moon_phase['name']}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Astronomy data error: {str(e)}"
            }
    
    def _get_weather_description(self, code: int) -> str:
        """Convert WMO weather code to description"""
        weather_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }
        return weather_codes.get(code, "Unknown")
    
    def _get_aqi_category(self, aqi: int) -> Dict[str, str]:
        """Get AQI category and health information"""
        if aqi <= 50:
            return {
                "category": "Good",
                "health_impact": "Air quality is satisfactory",
                "recommendation": "Enjoy outdoor activities"
            }
        elif aqi <= 100:
            return {
                "category": "Moderate",
                "health_impact": "Acceptable for most people",
                "recommendation": "Sensitive individuals should limit prolonged outdoor exertion"
            }
        elif aqi <= 150:
            return {
                "category": "Unhealthy for Sensitive Groups",
                "health_impact": "May cause breathing issues for sensitive groups",
                "recommendation": "Children, elderly, and people with respiratory conditions should reduce outdoor activities"
            }
        elif aqi <= 200:
            return {
                "category": "Unhealthy",
                "health_impact": "Everyone may experience health effects",
                "recommendation": "Avoid prolonged outdoor activities"
            }
        elif aqi <= 300:
            return {
                "category": "Very Unhealthy",
                "health_impact": "Health alert: everyone may experience serious effects",
                "recommendation": "Stay indoors and keep windows closed"
            }
        else:
            return {
                "category": "Hazardous",
                "health_impact": "Emergency conditions",
                "recommendation": "Everyone should avoid all outdoor activities"
            }
    
    def _calculate_moon_phase(self, date_str: str) -> Dict[str, Any]:
        """Calculate moon phase (simplified approximation)"""
        # Parse date
        date = datetime.fromisoformat(date_str)
        
        # Known new moon: January 6, 2000
        known_new_moon = datetime(2000, 1, 6, 18, 14)
        
        # Lunar cycle is approximately 29.53 days
        lunar_cycle = 29.53
        
        # Calculate days since known new moon
        days_since = (date - known_new_moon).total_seconds() / 86400
        
        # Calculate current phase
        phase_position = (days_since % lunar_cycle) / lunar_cycle
        illumination = round(100 * (1 - abs(2 * phase_position - 1)))
        
        # Determine phase name
        if phase_position < 0.03 or phase_position > 0.97:
            name, emoji = "New Moon", "🌑"
        elif phase_position < 0.22:
            name, emoji = "Waxing Crescent", "🌒"
        elif phase_position < 0.28:
            name, emoji = "First Quarter", "🌓"
        elif phase_position < 0.47:
            name, emoji = "Waxing Gibbous", "🌔"
        elif phase_position < 0.53:
            name, emoji = "Full Moon", "🌕"
        elif phase_position < 0.72:
            name, emoji = "Waning Gibbous", "🌖"
        elif phase_position < 0.78:
            name, emoji = "Last Quarter", "🌗"
        else:
            name, emoji = "Waning Crescent", "🌘"
        
        return {
            "name": name,
            "illumination": illumination,
            "emoji": emoji
        }