import json
import logging
import os
from typing import Optional

import aiohttp
from aegis.registry import register_tool

logger = logging.getLogger(__name__)

@register_tool("search_internet")
async def search_internet(query: str, serpapi_api_key: str = None, context_variables: dict = None) -> str:
    """
    Searches the internet using SerpAPI.

    Args:
        query: The search query.
        serpapi_api_key: The API key for SerpAPI.

    Returns:
        The search results as a string.
    """
    if not serpapi_api_key:
        return "SERPAPI_API_KEY not set. Please set it in the .env file."

    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": serpapi_api_key,
        "hl": "en",  # Language
        "gl": "us"   # Country
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                data = await response.json()
                # Extract relevant information from the search results
                # This is a simplified example; adjust based on the actual API response structure
                if "organic_results" in data:
                    results = [result.get("snippet", "") for result in data["organic_results"]]
                    return "\n".join(results)
                elif "answer_box" in data:
                    return data["answer_box"].get("answer", "")
                elif "knowledge_graph" in data:
                    return data["knowledge_graph"].get("description", "")
                else:
                    return "No relevant results found."

    except aiohttp.ClientError as e:
        logger.error(f"Error during SerpAPI request: {e}")
        return f"Error during search: {e}"
    except Exception as e:
        logger.exception(f"Unexpected error during search: {e}")
        return f"Unexpected error during search: {e}"

@register_tool("calculate_distance")
async def calculate_distance(origin: str, destination: str, google_maps_api_key: Optional[str] = None, context_variables: dict = None) -> str:
    """
    Calculates the distance between two locations using the Google Maps Distance Matrix API.

    Args:
        origin: The starting location.
        destination: The destination location.
        google_maps_api_key: The API key for Google Maps Distance Matrix API.

    Returns:
        The distance between the two locations as a string.
    """
    if not google_maps_api_key:
        return "GOOGLE_MAPS_API_KEY not set. Please set it in the .env file."

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origin,
        "destinations": destination,
        "key": google_maps_api_key,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                if data["status"] == "OK":
                    distance = data["rows"][0]["elements"][0]["distance"]["text"]
                    duration = data["rows"][0]["elements"][0]["duration"]["text"]
                    return f"Distance: {distance}, Duration: {duration}"
                else:
                    return f"Error: {data['error_message']}"

    except aiohttp.ClientError as e:
        logger.error(f"Error during Google Maps request: {e}")
        return f"Error: {e}"
    except Exception as e:
        logger.exception(f"Unexpected error during distance calculation: {e}")
        return f"Unexpected error: {e}"


@register_tool("get_current_weather")
async def get_current_weather(location: str, api_key: str = None, context_variables: dict = None) -> str:
    """
    Retrieves the current weather for a given location using a weather API.  This is a placeholder tool.
    A real implementation would integrate with a weather API such as OpenWeatherMap.

    Args:
        location: The location to get the weather for.
        api_key:  Optional API key for the weather service.

    Returns:
        A string describing the current weather.
    """
    if not api_key:
        return f"Weather information for {location}: API key not provided, using sample data: Sunny, 25°C"

    # In a real implementation, you would make an API call here.
    # This is just a placeholder.

    return f"Weather information for {location}: Using sample data: Sunny, 25°C"