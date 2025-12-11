# Hugging Face Web Scraping Agent

## Description

This agent scrapes the Hugging Face website to collect data on newly uploaded and popular models. It extracts information such as model names, associated tasks, and the number of likes. The agent respects `robots.txt` and implements rate limiting to avoid overloading the server.

## Features

- **Web Scraping:** Scrapes model data from Hugging Face.
- **Rate Limiting:** Respects rate limits to avoid overloading the server.
- **Robots.txt Compliance:** Checks `robots.txt` before scraping.
- **Multiple Output Formats:** Supports saving data in JSON, CSV, and TXT formats.
- **Logging:** Provides detailed logging for debugging and monitoring.
- **Configuration:** Uses a configuration class for easy customization.
- **Error Handling:** Includes comprehensive error handling for network issues and data extraction.

## Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd huggingface_agent
    ```

2.  **Create a virtual environment (recommended):**

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

    Create a `.env` file based on `.env.example` and populate it with any required API keys or configuration values.

## Usage

```bash
python main.py --output_format json --log_level INFO --max_pages 5
```

### Arguments

-   `--output_format`:  The output format for the scraped data (json, csv, txt). Default is `json`.
-   `--log_level`:  The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default is `INFO`.
-   `--max_pages`: The maximum number of pages to scrape. Default is 5.

## Configuration

The agent can be configured using the `config.py` file. You can modify parameters such as:

-   `huggingface_url`: The base URL of the Hugging Face models page.
-   `output_dir`: The directory to save the output files.
-   `output_format`: The default output format.
-   `max_pages`: The default maximum number of pages to scrape.
-   `request_interval`:  The time in seconds to wait between requests.
-   `user_agent`: The user agent string for the requests.

## Architecture

-   `main.py`: Entry point with CLI argument parsing.
-   `config.py`: Configuration management using a dataclass.
-   `agents/main_agent.py`: The main agent responsible for orchestrating the scraping and saving process.
-   `tools/custom_tools.py`: Contains custom tools for scraping and saving data, including `scrape_huggingface_models`, `save_data`, and `check_robots_txt`.
-   `utils/logger.py`: Configures logging for the application.
-   `utils/helpers.py`: Provides helper functions like `clean_text`.

## Error Handling

The agent includes error handling for various scenarios, including:

-   Network errors during web scraping.
-   Errors during data extraction.
-   Invalid output formats.
-   `robots.txt` restrictions.

## Future Enhancements

-   Implement more sophisticated data extraction techniques.
-   Add support for different sorting options on Hugging Face.
-   Implement a more robust rate limiting mechanism.
-   Integrate with a database for storing scraped data.
-   Add support for proxies.