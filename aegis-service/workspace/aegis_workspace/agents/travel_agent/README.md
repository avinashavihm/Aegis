# Travel Agent Application

## Description
This application provides a travel agent that can plan, research, and book travel arrangements. It utilizes a multi-agent system with specialized agents for planning, research, and booking.

## Features
- Travel planning
- Travel research
- Booking of flights, hotels, and activities
- Configurable via environment variables

## Installation

1.  Clone the repository:

    ```bash
    git clone <repository_url>
    cd travel_agent
    ```

2.  Create a virtual environment:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # venv\Scripts\activate  # On Windows
    ```

3.  Install the dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4.  Create a `.env` file based on `.env.example` and fill in the required API keys.

## Configuration

The application is configured using environment variables.  The following variables are supported:

-   `OPENAI_API_KEY`: OpenAI API key. Required.
-   `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Defaults to INFO.
-   `TRAVEL_API_KEY`: API key for the travel service. Required for using travel-related tools.
-   `SERPAPI_API_KEY`: API key for the SerpAPI service. Required for research tasks.
-   `DEFAULT_CITY`: Default city for travel planning. Defaults to London.
-   `MAX_RETRIES`: Maximum number of retries for API calls. Defaults to 3.
-   `RETRY_DELAY`: Delay in seconds between retries. Defaults to 5.
-   `PLANNING_AGENT_MODEL`: OpenAI model used by the planning agent. Defaults to gpt-4.
-   `BOOKING_AGENT_MODEL`: OpenAI model used by the booking agent. Defaults to gpt-3.5-turbo.

## Usage

Run the `main.py` script with the `--task` argument to specify the travel planning task.

```bash
python main.py --task "Plan a trip to Paris for 3 days, including flights and hotels."
```

## Architecture

The application uses a multi-agent system with the following agents:

-   **MainAgent**: Orchestrates the travel planning process.
-   **PlanningAgent**: Creates the initial travel plan based on the user's request.
-   **ResearchAgent**: Researches specific details related to the travel plan, such as hotels, flights, and activities.
-   **BookingAgent**: Books flights, hotels, and activities based on the research results.

## Custom Tools

The application includes the following custom tools:

-   `get_weather`: Retrieves the current weather conditions for a given city.
-   `book_flight`: Books a flight between two cities on a specific date.
-   `find_local_attractions`: Finds local attractions in a given city.

## Logging

The application uses the `logging` module for logging. The log level can be configured using the `LOG_LEVEL` environment variable.

## Error Handling

The application includes error handling and retry mechanisms to ensure robustness.  API calls are retried up to `MAX_RETRIES` times with a delay of `RETRY_DELAY` seconds between retries.

## Future Enhancements

-   Implement more sophisticated travel planning algorithms.
-   Integrate with real-world travel APIs for booking flights and hotels.
-   Add support for more travel-related tools.
-   Improve the user interface.