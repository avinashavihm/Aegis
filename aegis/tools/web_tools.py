"""
Web operation tools
"""

from aegis.registry import register_tool
from aegis.environment.web_env import WebEnv


@register_tool("fetch_url")
def fetch_url(url: str, context_variables: dict = None) -> str:
    """
    Fetch content from a URL.
    
    Args:
        url: URL to fetch.
    """
    web_env: WebEnv = context_variables.get("web_env") if context_variables else None
    if not web_env:
        web_env = WebEnv()
    result = web_env.fetch_url(url)
    if result.get("status") == "success":
        return f"Title: {result.get('title', 'N/A')}\n\nContent:\n{result.get('content', 'N/A')}"
    else:
        error_msg = result.get("error", "Unknown error")
        status_code = result.get("status_code")
        hint = result.get("hint")
        meta = []
        if status_code:
            meta.append(f"status={status_code}")
        if hint:
            meta.append(f"hint={hint}")
        meta_suffix = f" ({'; '.join(meta)})" if meta else ""
        return f"Error fetching URL: {error_msg}{meta_suffix}"


@register_tool("search_web")
def search_web(
    query: str,
    num_results: int = 5,
    focus_keywords: list[str] | str | None = None,
    region: str | None = None,
    context_variables: dict = None
) -> str:
    """
    Search the web using DuckDuckGo (no API key required).
    
    This tool performs real web searches and returns results with titles, URLs, and snippets.
    You can then use fetch_url to get the full content of any result.
    
    Args:
        query: Search query.
        num_results: Number of results to return (default: 5, max: 20).
        focus_keywords: Optional list (or comma-separated string) of keywords to prioritize.
        region: Optional DuckDuckGo region code (e.g., 'in-en', 'us-en').
    """
    web_env: WebEnv = context_variables.get("web_env") if context_variables else None
    if not web_env:
        web_env = WebEnv()
    
    # Limit num_results to reasonable value
    num_results = min(max(1, num_results), 20)
    
    if isinstance(focus_keywords, str):
        focus_keywords = [kw.strip() for kw in focus_keywords.split(",") if kw.strip()]
    elif focus_keywords is None and context_variables:
        focus_keywords = context_variables.get("search_focus_keywords")
    if region is None and context_variables:
        region = context_variables.get("search_region")
    
    result = web_env.search_web(
        query,
        num_results,
        focus_keywords=focus_keywords,
        region=region
    )
    
    if result.get("status") == "success":
        return result.get("formatted", result.get("message", "Search completed successfully."))
    elif result.get("status") == "info":
        meta = result.get("meta", {})
        filtered = meta.get("filtered_out")
        if filtered:
            return f"{result.get('message', 'No results found.')} (Filtered out {filtered} low-relevance hits. Try loosening focus_keywords.)"
        return result.get("message", "No results found.")
    else:
        error_msg = result.get("error", "Unknown error")
        return f"Error performing web search: {error_msg}"


@register_tool("extract_content")
def extract_content(html: str, context_variables: dict = None) -> str:
    """
    Extract text content from HTML string.
    
    NOTE: This tool extracts text from HTML strings. If you have a URL, use fetch_url instead.
    
    Args:
        html: HTML content string to extract text from.
    """
    web_env: WebEnv = context_variables.get("web_env") if context_variables else None
    if not web_env:
        web_env = WebEnv()
    return web_env.extract_content(html)


@register_tool("fetch_and_extract")
def fetch_and_extract(url: str, context_variables: dict = None) -> str:
    """
    Fetch content from a URL and extract the text. This is a convenience tool that combines fetch_url and extract_content.
    
    Use this tool when you have a URL from search results and want to get the full article content.
    
    Args:
        url: URL to fetch and extract content from.
    """
    web_env: WebEnv = context_variables.get("web_env") if context_variables else None
    if not web_env:
        web_env = WebEnv()
    
    result = web_env.fetch_url(url)
    if result.get("status") == "success":
        return f"Title: {result.get('title', 'N/A')}\n\nContent:\n{result.get('content', 'N/A')}"
    else:
        return f"Error fetching URL: {result.get('error', 'Unknown error')}"

