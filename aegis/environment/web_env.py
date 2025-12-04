"""
Web environment for web browsing (simplified, requests-based)
"""

import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
import time
from urllib.parse import unquote, parse_qs, urlparse

try:  # Prefer the actively maintained package name
    from ddgs import DDGS  # type: ignore
except Exception:  # pragma: no cover - fallback to legacy package
    from duckduckgo_search import DDGS  # type: ignore


class WebEnv:
    """Web browsing environment using requests"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_url(self, url: str) -> Dict[str, any]:
        """
        Fetch content from a URL
        
        Args:
            url: URL to fetch
            
        Returns:
            Dictionary with 'status', 'content', 'title', etc.
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = soup.find('title')
            title_text = title.string if title else "No title"
            
            # Extract main content (simplified)
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return {
                "status": "success",
                "url": url,
                "title": title_text,
                "content": text[:5000],  # Limit content length
                "status_code": response.status_code
            }
        except requests.exceptions.HTTPError as e:
            status_code = getattr(e.response, "status_code", None)
            hint = "Site blocked automated scraping (HTTP 403). Consider summarizing snippet text instead." \
                if status_code == 403 else "HTTP error while fetching the page."
            return {
                "status": "error",
                "url": url,
                "error": str(e),
                "status_code": status_code,
                "hint": hint
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "url": url,
                "error": str(e),
                "hint": "Network error. Check connectivity or try again with a different site."
            }
    
    def search_web(
        self,
        query: str,
        num_results: int = 5,
        focus_keywords: Optional[List[str]] = None,
        region: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Search the web using DuckDuckGo (no API key required)
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            Dictionary with search results
        """
        focus_keywords = [kw.strip().lower() for kw in (focus_keywords or []) if kw and kw.strip()]
        region = region or "wt-wt"
        NOISE_DOMAINS = {"zhihu.com", "gov.uk", "yahoo.co.jp", "finance.yahoo.com"}
        
        try:
            results = []
            with DDGS() as ddgs:
                search_results = list(ddgs.text(query, max_results=num_results, region=region))
                
                for result in search_results:
                    url = result.get("href", "")
                    # Decode DuckDuckGo redirect URLs if present
                    if url.startswith("//duckduckgo.com/l/") or url.startswith("duckduckgo.com/l/"):
                        try:
                            # Extract the actual URL from the redirect
                            parsed = urlparse(url if url.startswith("http") else f"https:{url}")
                            query_params = parse_qs(parsed.query)
                            if 'uddg' in query_params:
                                actual_url = unquote(query_params['uddg'][0])
                                url = actual_url
                        except:
                            pass  # Keep original URL if decoding fails
                    
                    title = result.get("title", "")
                    snippet = result.get("body", "")
                    
                    domain = urlparse(url if url.startswith("http") else f"https:{url}").netloc.lower()
                    if any(noise in domain for noise in NOISE_DOMAINS):
                        continue
                    
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet
                    })
            
            if results:
                def score(entry):
                    if not focus_keywords:
                        return 0
                    haystack = f"{entry['title']} {entry['snippet']} {entry['url']}".lower()
                    return sum(1 for kw in focus_keywords if kw in haystack)
                
                scored_results = sorted(results, key=score, reverse=True)
                filtered_results = [
                    r for r in scored_results
                    if not focus_keywords or score(r) > 0
                ]
                if focus_keywords and not filtered_results:
                    filtered_results = scored_results  # fall back to whatever we have
                
                formatted_results = f"Found {len(filtered_results)} results for '{query}':\n\n"
                formatted_results += "IMPORTANT: Use fetch_url(url) or fetch_and_extract(url) to retrieve full content. Obey site terms and rate limits.\n\n"
                for i, result in enumerate(filtered_results, 1):
                    formatted_results += f"{i}. {result['title']}\n"
                    formatted_results += f"   URL: {result['url']}\n"
                    formatted_results += f"   Preview: {result['snippet'][:200]}...\n\n"
                
                # Format results as a readable string with clear instructions
                return {
                    "status": "success",
                    "query": query,
                    "results": filtered_results,
                    "formatted": formatted_results,
                    "message": formatted_results,
                    "meta": {
                        "filtered_out": max(0, len(results) - len(filtered_results)),
                        "focus_keywords": focus_keywords
                    }
                }
            else:
                return {
                    "status": "info",
                    "query": query,
                    "message": f"No results found for '{query}'"
                }
        except ImportError:
            # Fallback to DuckDuckGo HTML scraping if library not available
            try:
                search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
                response = self.session.get(search_url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                # DuckDuckGo HTML structure (may change)
                result_divs = soup.find_all('div', class_='result')[:num_results]
                
                for div in result_divs:
                    title_elem = div.find('a', class_='result__a')
                    snippet_elem = div.find('a', class_='result__snippet')
                    
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        url = title_elem.get('href', '')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                        
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet
                        })
                
                if results:
                    formatted_results = f"Found {len(results)} results for '{query}':\n\n"
                    for i, result in enumerate(results, 1):
                        formatted_results += f"{i}. {result['title']}\n"
                        formatted_results += f"   URL: {result['url']}\n"
                        formatted_results += f"   {result['snippet'][:200]}...\n\n"
                    
                    return {
                        "status": "success",
                        "query": query,
                        "results": results,
                        "formatted": formatted_results,
                        "message": formatted_results
                    }
                else:
                    return {
                        "status": "info",
                        "query": query,
                        "message": f"No results found for '{query}'"
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "query": query,
                    "error": str(e),
                    "message": f"Error performing web search: {str(e)}"
                }
        except Exception as e:
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "message": f"Error performing web search: {str(e)}. Consider narrowing the query or trying different keywords."
            }
    
    def extract_content(self, html: str) -> str:
        """Extract text content from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return ' '.join(chunk for chunk in chunks if chunk)

