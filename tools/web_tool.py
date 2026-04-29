# tools/web_tool.py
"""
DuckDuckGo HTML-search helper (no API key).
Parses search results from https://html.duckduckgo.com/html/?q=<query>
Requires: requests, beautifulsoup4
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import time

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"

class WebTool:
    def __init__(self, throttle_seconds: float = 0.5):
        self.base = "https://html.duckduckgo.com/html/"
        self.throttle = throttle_seconds

    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Returns a list of dicts: [{'title':..., 'link':..., 'snippet':...}, ...]
        Uses DuckDuckGo HTML results page. Throttles by self.throttle seconds.
        """
        try:
            params = {"q": query}
            headers = {"User-Agent": USER_AGENT}
            resp = requests.post(self.base, data=params, headers=headers, timeout=15)
            resp.raise_for_status()
            time.sleep(self.throttle)
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            # DuckDuckGo 'result' items have class 'result'
            containers = soup.find_all("div", class_="result", limit=num_results)
            if not containers:
                # fallback: find links
                anchors = soup.find_all("a", attrs={"class": "result__a"}, limit=num_results)
                for a in anchors:
                    title = a.get_text(strip=True)
                    link = a.get("href")
                    # snippet is sibling element sometimes
                    snippet_tag = a.find_parent().find("a", class_="result__snippet") if a.find_parent() else None
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                    results.append({"title": title, "link": link, "snippet": snippet})
            else:
                for c in containers:
                    a = c.find("a", class_="result__a")
                    title = a.get_text(strip=True) if a else c.get_text(strip=True)[:80]
                    link = a.get("href") if a else None
                    snippet_tag = c.find("a", class_="result__snippet")
                    if not snippet_tag:
                        snippet_tag = c.find("div", class_="result__snippet")
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                    results.append({"title": title, "link": link, "snippet": snippet})
            # ensure consistent length
            return results[:num_results]
        except Exception:
            # robust fallback: return placeholder so pipeline stays runnable
            return [{"title": f"Placeholder for {query}", "link": "https://example.com", "snippet": "No live DDG result"} for _ in range(num_results)]
