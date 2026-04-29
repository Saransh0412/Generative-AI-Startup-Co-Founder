# tools/file_tool.py
from pathlib import Path
import json
from typing import Any

def save_json(path: str, data: Any):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)

def save_text(path: str, text: str):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf8")
