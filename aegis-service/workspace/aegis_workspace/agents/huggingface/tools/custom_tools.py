import asyncio
import logging
import json
import csv
import os
import time
import urllib.robotparser
from typing import List, Dict

import aiohttp
from bs4 import BeautifulSoup
from aegis.registry import register_tool

logger = logging.getLogger(__name__)

async def check_robots_txt(url: str, user_agent: str) -> bool:
    """
    Checks if the agent is allowed to scrape the given URL based on the robots.txt file.
    """
    try:
        rp = urllib.robotparser.RobotFileParser()
        robots_url = f"{url.split('/')[0]}//{url.split('/')[2]}/robots.txt" # Construct robots.txt URL
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception as e:
        logger.warning(f"Error checking robots.txt: {e}. Assuming scraping is allowed.")
        return True # Assume allowed if robots.txt check fails

@register_tool("scrape_huggingface_models")
async def scrape_huggingface_models(url: str, max_pages: int = 5, request_interval: float = 2.0, user_agent: str = None) -> List[Dict]:
    """
    Scrapes the Hugging Face models page and extracts model data.

    Args:
        url: The base URL of the Hugging Face models page.
        max_pages: The maximum number of pages to scrape.
        request_interval: Time in seconds to wait between requests.
        user_agent: User agent string for the requests.

    Returns:
        A list of dictionaries, where each dictionary contains the data for a model.
    """
    models_data = []
    async with aiohttp.ClientSession() as session:
        for page in range(1, max_pages + 1):
            page_url = f"{url}?p={page}&sort=trending"
            logger.info(f"Scraping page: {page_url}")

            if not await check_robots_txt(page_url, user_agent):
                logger.warning(f"Scraping disallowed by robots.txt for {page_url}. Skipping.")
                continue

            try:
                async with session.get(page_url, headers={"User-Agent": user_agent}) as response:
                    response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    model_cards = soup.find_all("article", class_="card")
                    for card in model_cards:
                        try:
                            model_name_element = card.find("h4", class_="block font-semibold leading-5 truncate")
                            model_name = model_name_element.text.strip() if model_name_element else "N/A"

                            task_element = card.find("p", class_="text-sm text-gray-500 truncate")
                            task = task_element.text.strip() if task_element else "N/A"

                            likes_element = card.find("span", class_="!mb-0 text-sm")
                            likes = int(likes_element.text.strip()) if likes_element else 0

                            model_data = {
                                "model_name": model_name,
                                "task": task,
                                "likes": likes,
                            }
                            models_data.append(model_data)
                            logger.debug(f"Extracted data: {model_data}")

                        except Exception as e:
                            logger.warning(f"Error extracting data from card: {e}")


            except aiohttp.ClientError as e:
                logger.error(f"Error fetching page {page_url}: {e}")
                continue  # Skip to the next page

            await asyncio.sleep(request_interval) # Respect rate limits

    return models_data

@register_tool("save_data")
async def save_data(data: List[Dict], output_dir: str, output_format: str = "json") -> str:
    """
    Saves the scraped data to a file in the specified format.

    Args:
        data: The list of dictionaries containing the scraped data.
        output_dir: The directory to save the output file.
        output_format: The format to save the data in (json, csv, txt).

    Returns:
        The path to the saved file.
    """
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"huggingface_models_{timestamp}.{output_format}"
    filepath = os.path.join(output_dir, filename)

    try:
        if output_format == "json":
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        elif output_format == "csv":
            if data:
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        elif output_format == "txt":
            with open(filepath, "w", encoding="utf-8") as f:
                for item in data:
                    f.write(str(item) + "\n")
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        logger.info(f"Data saved to: {filepath}")
        return filepath

    except Exception as e:
        logger.error(f"Error saving data to file: {e}")
        raise