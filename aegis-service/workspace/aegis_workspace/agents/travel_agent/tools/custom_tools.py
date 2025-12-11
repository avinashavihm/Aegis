import logging
from aegis.registry import register_tool
import requests
from config import Config

logger = logging.getLogger(__name__)

@register_tool("get_weather")
def get_weather(city: str, api_key: str = None, context_variables: dict = None) -> str:
    """
    Retrieves the current weather conditions for a given city.

    Args:
        city (str): The name of the city to retrieve weather information for.
        api_key (str, optional): The API key for the weather service. Defaults to None.
        context_variables (dict, optional): Context variables, including configuration. Defaults to None.

    Returns:
        str: A string containing the weather information for the specified city.
    """
    try:
        if not city:
            return "Error: City name is required."

        if not api_key and context_variables and context_variables.get("config") and isinstance(context_variables["config"], Config):
            api_key = context_variables["config"].travel_api_key
        elif not api_key:
            return "Error: API key is required."

        # Example using a placeholder weather API
        url = f"https://api.example.com/weather?city={city}&apiKey={api_key}"
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        weather_data = response.json()

        # Format the weather information
        weather_description = weather_data.get("description", "No description available.")
        temperature = weather_data.get("temperature", "N/A")
        humidity = weather_data.get("humidity", "N/A")

        weather_info = f"The weather in {city} is {weather_description}. The temperature is {temperature}°C and the humidity is {humidity}%."
        logger.info(f"Successfully retrieved weather for {city}.")
        return weather_info

    except requests.exceptions.RequestException as e:
        logger.error(f"Error retrieving weather for {city}: {e}")
        return f"Error: Could not retrieve weather information for {city}."
    except Exception as e:
        logger.exception(f"An unexpected error occurred while retrieving weather for {city}: {e}")
        return f"Error: An unexpected error occurred while retrieving weather for {city}."

@register_tool("book_flight")
def book_flight(departure_city: str, destination_city: str, date: str, context_variables: dict = None) -> str:
    """
    Books a flight between two cities on a specific date.

    Args:
        departure_city (str): The city of departure.
        destination_city (str): The destination city.
        date (str): The date of the flight (YYYY-MM-DD).
        context_variables (dict, optional): Context variables, including configuration. Defaults to None.

    Returns:
        str: A string containing the booking confirmation or an error message.
    """
    try:
        if not all([departure_city, destination_city, date]):
            return "Error: Departure city, destination city, and date are required."

        # Simulate flight booking
        booking_confirmation = f"Successfully booked flight from {departure_city} to {destination_city} on {date}. Confirmation number: FLT12345."
        logger.info(f"Successfully booked flight from {departure_city} to {destination_city} on {date}.")
        return booking_confirmation

    except Exception as e:
        logger.exception(f"Error booking flight from {departure_city} to {destination_city} on {date}: {e}")
        return f"Error: Could not book flight from {departure_city} to {destination_city} on {date}."

@register_tool("find_local_attractions")
def find_local_attractions(city: str, context_variables: dict = None) -> str:
    """
    Finds local attractions in a given city.

    Args:
        city (str): The city to find attractions in.
        context_variables (dict, optional): Context variables, including configuration. Defaults to None.

    Returns:
        str: A string containing a list of local attractions or an error message.
    """
    try:
        if not city:
            return "Error: City name is required."

        # Simulate finding local attractions
        attractions = ["Eiffel Tower", "Louvre Museum", "Notre-Dame Cathedral"]  # Example attractions
        attractions_list = ", ".join(attractions)
        attractions_info = f"Local attractions in {city} include: {attractions_list}."
        logger.info(f"Successfully found local attractions in {city}.")
        return attractions_info

    except Exception as e:
        logger.exception(f"Error finding local attractions in {city}: {e}")
        return f"Error: Could not find local attractions in {city}."