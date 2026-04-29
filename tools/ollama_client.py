# tools/ollama_client.py
"""
Ollama client that correctly handles streaming NDJSON chunk responses.

Behavior:
- POST /api/generate
- If response body contains multiple JSON objects on separate lines (NDJSON),
  parse them in order and assemble 'response' fragments into one final text.
- Saves raw HTTP body to logs/ollama_raw_response.txt and a debug JSON to outputs/debug_ollama.json.
- Returns dict with keys:
    - 'text': assembled response string ('' if nothing assembled)
    - 'chunks': list of parsed JSON objects (in order)
    - 'last_chunk': last parsed JSON object (if any)
"""
import requests
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

LOG_PATH = Path("logs")
LOG_PATH.mkdir(parents=True, exist_ok=True)
OUT_PATH = Path("outputs")
OUT_PATH.mkdir(parents=True, exist_ok=True)

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 120):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def _save_raw(self, label: str, text: str):
        p = LOG_PATH / "ollama_raw_response.txt"
        with open(p, "a", encoding="utf8") as f:
            f.write(f"--- {label} ---\n")
            f.write(text + "\n\n")

    def _save_debug_json(self, data: dict):
        p = OUT_PATH / "debug_ollama.json"
        with open(p, "w", encoding="utf8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def generate(self, model: str, prompt: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/generate"
        payload = {"model": model, "prompt": prompt}
        if params:
            payload.update(params)

        resp = requests.post(url, json=payload, timeout=self.timeout)
        # Save headers/status
        header_info = {"status": resp.status_code, "headers": dict(resp.headers)}
        self._save_raw("HTTP-HEADERS", json.dumps(header_info))
        body = resp.text or ""
        self._save_raw("HTTP-BODY", body)

        # If body is empty, return empty text
        if not body.strip():
            self._save_debug_json({"status": resp.status_code, "body": ""})
            return {"text": "", "chunks": [], "last_chunk": None}

        # Try to parse as normal JSON (single object)
        try:
            data = resp.json()
            # if JSON is dict or list but not NDJSON, try to extract 'response' or known text keys
            if isinstance(data, dict):
                # prefer direct text-like fields
                for key in ("text", "output", "response", "generated_text", "answer"):
                    if key in data and data[key]:
                        val = data[key]
                        if isinstance(val, str):
                            self._save_debug_json({"chunks": [data]})
                            return {"text": val, "chunks": [data], "last_chunk": data}
                        else:
                            # coerce complex structure to string
                            txt = json.dumps(val, ensure_ascii=False)
                            self._save_debug_json({"chunks": [data]})
                            return {"text": txt, "chunks": [data], "last_chunk": data}
            # if it's a list or other shape, just return its string
            self._save_debug_json({"raw_json": data})
            return {"text": json.dumps(data, ensure_ascii=False), "chunks": [data] if isinstance(data, dict) else [], "last_chunk": data}
        except Exception:
            # Not single JSON (likely NDJSON streaming). We'll parse line-by-line.
            pass

        chunks: List[Dict[str, Any]] = []
        assembled = []
        last_chunk = None

        # parse each non-empty line as JSON; if JSON parsing fails for a line, keep raw
        for line in [ln for ln in body.splitlines() if ln.strip()]:
            parsed = None
            try:
                parsed = json.loads(line)
            except Exception:
                # sometimes the server may prepend non-json; skip or store as raw chunk
                parsed = {"raw_line": line}
            chunks.append(parsed)
            last_chunk = parsed
            # if parsed is dict and has 'response' field, append its text fragment
            if isinstance(parsed, dict):
                resp_fragment = parsed.get("response")
                if isinstance(resp_fragment, str) and resp_fragment != "":
                    assembled.append(resp_fragment)

        final_text = "".join(assembled).strip()
        # Save debug JSON with chunks and assembled text
        debug_data = {"model": model, "assembled_text": final_text, "chunks_count": len(chunks), "chunks_sample": chunks[-10:]}
        self._save_debug_json(debug_data)

        return {"text": final_text, "chunks": chunks, "last_chunk": last_chunk}
