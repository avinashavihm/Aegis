import re

def clean_text(text: str) -> str:
    """
    Cleans the given text by removing extra whitespace and special characters.

    Args:
        text: The text to clean.

    Returns:
        The cleaned text.
    """
    text = re.sub(r"\s+", " ", text).strip()  # Remove extra whitespace
    # Add more cleaning as needed
    return text