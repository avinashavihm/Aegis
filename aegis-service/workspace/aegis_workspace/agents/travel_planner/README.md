# Travel Planner Agent

## Description

The Travel Planner Agent is a multi-agent system designed to automate the process of travel planning, including research, planning, and booking. It leverages specialized agents for each stage of the process, coordinated by a main orchestrator agent.

## Features

- **Research:**  Researches travel destinations, accommodations, and activities using the SerpAPI tool.
- **Planning:** Creates detailed travel plans with daily itineraries, accommodation recommendations, and transportation options.
- **Booking:**  Simulates the booking of flights, hotels, and activities (currently a simplified implementation).
- **Orchestration:**  The main agent manages the workflow and coordinates communication between the specialized agents.
- **Custom Tools:** Includes tools for searching the internet, calculating distances, and getting weather information.
- **Configuration:** Uses a `config.py` file to manage API keys and other settings.
- **Logging:**  Provides comprehensive logging for debugging and monitoring.

## Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd travel_planner
    ```

2.  **Create a virtual environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate  # On Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**

    -   Create a `.env` file based on the `.env.example` file.
    -   Set the `OPENAI_API_KEY`, `SERPAPI_API_KEY` (optional), and `GOOGLE_MAPS_API_KEY` (optional) environment variables.

## Usage

```bash
python main.py --task "Plan a trip to Paris for 5 days" --verbose
```

-   `--task`:  The travel planning task to execute (required).
-   `--verbose`:  Enable verbose logging (optional).

## Architecture

The system consists of the following agents:

-   **MainAgent:**  The orchestrator agent that manages the overall workflow.
-   **ResearchAgent:**  Researches travel information.
-   **PlanningAgent:**  Creates the detailed travel plan.
-   **BookingAgent:**  Handles bookings (currently simulated).

The agents communicate with each other to complete the travel planning task.  They also utilize custom tools for tasks such as searching the internet and calculating distances.

## Custom Tools

-   `search_internet`: Searches the internet using SerpAPI.
-   `calculate_distance`: Calculates the distance between two locations using the Google Maps Distance Matrix API.
-   `get_current_weather`: Retrieves the current weather for a given location (placeholder implementation).

## Configuration

The `config.py` file contains configuration settings for the agent, including API keys, model names, and temperature settings.

## Logging

The agent uses the `logging` module to provide comprehensive logging.  The logging level can be configured using the `--verbose` flag.

## Future Enhancements

-   Implement integration with real booking APIs.
-   Add support for more advanced travel planning features.
-   Improve the accuracy and reliability of the custom tools.
-   Implement a more sophisticated agent communication mechanism.