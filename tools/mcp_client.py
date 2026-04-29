# tools/mcp_client.py
import requests, json
from pathlib import Path
from typing import Dict, Any, Optional
from time import sleep

LOG_PATH = Path("logs")
LOG_PATH.mkdir(parents=True, exist_ok=True)

class MCPClient:
    def __init__(self, base_url: str = "http://localhost:9000", timeout: int = 20, max_retries: int = 2, headers: Optional[Dict[str,str]]=None):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {"Content-Type": "application/json"}
        if headers:
            self.headers.update(headers)

    def _log_raw(self, label: str, text: str):
        with open(LOG_PATH / "mcp_raw.txt", "a", encoding="utf8") as f:
            f.write(f"--- {label} ---\n{text}\n\n")

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path if path.startswith('/') else '/' + path}"
        last_exc = None
        for attempt in range(1, self.max_retries + 2):
            try:
                r = requests.post(url, json=payload, headers=self.headers, timeout=self.timeout)
                self._log_raw(f"POST {url} [attempt {attempt}] HEADERS", json.dumps(dict(r.headers)))
                self._log_raw(f"POST {url} [attempt {attempt}] BODY", r.text[:20000])
                r.raise_for_status()
                try:
                    return r.json()
                except Exception:
                    return {"raw": r.text}
            except Exception as e:
                last_exc = e
                sleep(0.5)
        raise RuntimeError(f"MCP POST {url} failed after retries. Last error: {last_exc}")

    def search(self, q: str, max_results: int = 5) -> Dict[str, Any]:
        return self._post("/api/search", {"q": q, "max_results": max_results})

    def compute(self, task: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/api/compute", {"task": task, "payload": payload})
