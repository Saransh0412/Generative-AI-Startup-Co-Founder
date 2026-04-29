# agents/base_agent.py
import json, logging
from datetime import datetime
from typing import Any, Dict, Callable, List

logger = logging.getLogger("agents")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)

class CallbackRegistry:
    def __init__(self):
        self._callbacks: List[Callable[[str, Dict[str,Any]], None]] = []

    def register(self, cb: Callable[[str, Dict[str,Any]], None]):
        self._callbacks.append(cb)

    def emit(self, event_name: str, payload: Dict[str,Any]):
        for cb in self._callbacks:
            try:
                cb(event_name, payload)
            except Exception:
                logger.exception("Callback failed")

class BaseAgent:
    def __init__(self, name: str, shared_state: dict, callbacks: CallbackRegistry):
        self.name = name
        self.state = shared_state
        self.callbacks = callbacks

    def log(self, level: str, message: str, payload: Dict[str,Any] = None):
        ts = datetime.utcnow().isoformat()
        entry = {"ts": ts, "agent": self.name, "level": level, "message": message}
        if payload is not None:
            entry["payload"] = payload
        self.callbacks.emit("log", entry)
        try:
            if level == "info":
                logger.info(json.dumps(entry, ensure_ascii=False))
            else:
                logger.error(json.dumps(entry, ensure_ascii=False))
        except Exception:
            pass

    def print_terminal(self, obj: Dict[str,Any]):
        print(f"\n--- {self.name} OUTPUT @ {datetime.utcnow().isoformat()} ---")
        print(json.dumps(obj, indent=2, ensure_ascii=False))
        print(f"--- end {self.name} output ---\n")

    # A2A envelope helper
    @staticmethod
    def make_envelope(frm: str, to: str, payload: dict, typ: str="context") -> dict:
        return {"from": frm, "to": to, "type": typ, "payload": payload, "ts": datetime.utcnow().isoformat()}
