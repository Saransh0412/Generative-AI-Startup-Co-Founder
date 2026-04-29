# agents/idea_agent.py
from .base_agent import BaseAgent
import uuid, re, json, time
from typing import Optional, Any, Dict, List

IGNORED_META_KEYS = {
    "model", "created_at", "done", "done_reason", "context",
    "prompt_tokens", "completion_tokens", "usage", "id"
}

def _is_possible_natural_text(s: str) -> bool:
    if not isinstance(s, str):
        return False
    s = s.strip()
    if len(s) < 30:
        return False
    if s.startswith("{") and s.endswith("}"):
        return False
    if s.count("{") and s.count("}") and '"' in s:
        return False
    low = s.lower()
    for token in ("created_at", "done_reason", "context", "token", "usage", "model"):
        if token in low:
            return False
    return True

def _find_text_recursive(obj: Any) -> Optional[str]:
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj if _is_possible_natural_text(obj) else None
    if isinstance(obj, dict):
        for key in ("text", "output", "response", "generated_text", "completion", "content", "answer"):
            if key in obj and obj[key]:
                v = obj[key]
                if isinstance(v, str) and _is_possible_natural_text(v):
                    return v
                if not isinstance(v, str):
                    found = _find_text_recursive(v)
                    if found:
                        return found
        for k, v in obj.items():
            if isinstance(v, str) and _is_possible_natural_text(v):
                return v
        for k, v in obj.items():
            if k in IGNORED_META_KEYS:
                continue
            found = _find_text_recursive(v)
            if found:
                return found
        return None
    if isinstance(obj, (list, tuple)):
        for el in reversed(obj):
            found = _find_text_recursive(el)
            if found:
                return found
        for el in obj:
            found = _find_text_recursive(el)
            if found:
                return found
    return None

class IdeaAgent(BaseAgent):
    def __init__(self, name, state, callbacks, ollama_client, model_name: str = "deepseek-r1:8b", model_fallback: Optional[str] = None):
        super().__init__(name, state, callbacks)
        if ollama_client is None:
            raise ValueError("IdeaAgent requires an Ollama client.")
        self.ollama = ollama_client
        self.model = model_name
        self.model_fallback = model_fallback  # optional; set to "gpt-oss:20b" if you want fallback

    def _parse_text_to_ideas(self, text: str):
        ideas = []
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for ln in lines:
            ln_clean = re.sub(r'^\s*\d+[\.\)]\s*', '', ln)
            parts = ln_clean.split(' - ')
            title = parts[0].strip() if parts else ln_clean[:80]
            desc = parts[1].strip() if len(parts) >= 2 else ""
            novelty = []
            if len(parts) >= 3:
                novelty = [p.strip() for p in parts[2].split(',') if p.strip()]
            if not novelty and ',' in desc:
                pieces = [p.strip() for p in desc.split(',')]
                if len(pieces) >= 2 and len(pieces[-1]) < 80:
                    novelty = pieces[-2:]
                    desc = ', '.join(pieces[:-2]).strip()
            ideas.append({
                "id": f"idea_{uuid.uuid4().hex[:8]}",
                "title": title[:160],
                "short_description": desc[:800],
                "novelty_points": novelty
            })
        return ideas

    def _save_debug_failure(self, payload: dict):
        p = "outputs/debug_idea_failure.json"
        with open(p, "w", encoding="utf8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return p

    def _attempt_generate(self, model: str, prompt: str, params: dict):
        """Call the Ollama client and return parsed response dict (no extraction)."""
        try:
            return self.ollama.generate(model, prompt, params=params)
        except Exception as e:
            self.log("error", "Ollama client raised", {"error": str(e), "model": model, "params": params})
            return {"error": str(e)}

    def run(self, domain: str):
        self.log("info", f"Starting idea generation for domain: {domain}")
        strict_prompt = (
            "You are a startup idea generator. Produce EXACTLY 3 numbered ideas (1., 2., 3.) for the domain provided.\n\n"
            "Format (EXACT):\n"
            "1. <Title> - <One-line description> - <novelty1, novelty2>\n\n"
            f"Domain: {domain}\n\n"
            "Return ONLY the 3 numbered lines, nothing else. NO JSON, NO metadata, NO code blocks."
        )

        # Attempt patterns (increase tokens/temperature)
        attempt_params = [
            {"max_tokens": 200, "temperature": 0.0},
            {"max_tokens": 512, "temperature": 0.2},
            {"max_tokens": 1024, "temperature": 0.6},
        ]

        responses = []
        text_response = None

        # Try multiple attempts on primary model
        for i, params in enumerate(attempt_params, start=1):
            self.log("info", f"IdeaAgent attempt {i} with params {params}", {"model": self.model})
            resp = self._attempt_generate(self.model, strict_prompt, params)
            responses.append({"attempt": i, "model": self.model, "params": params, "resp": resp})
            # extract natural text
            candidate = _find_text_recursive(resp)
            if candidate:
                text_response = candidate
                self.log("info", f"Extracted text on attempt {i}", {"len": len(candidate)})
                break
            # small wait between attempts
            time.sleep(0.5)

        # Optionally try fallback model if primary gave nothing
        if not text_response and self.model_fallback:
            self.log("info", "Trying fallback model", {"fallback": self.model_fallback})
            for i, params in enumerate(attempt_params, start=1):
                resp = self._attempt_generate(self.model_fallback, strict_prompt, params)
                responses.append({"attempt": f"fb{i}", "model": self.model_fallback, "params": params, "resp": resp})
                candidate = _find_text_recursive(resp)
                if candidate:
                    text_response = candidate
                    self.log("info", f"Extracted text from fallback model on attempt fb{i}", {"len": len(candidate)})
                    break
                time.sleep(0.5)

        # If still nothing, save debug and raise
        if not text_response:
            debug_payload = {
                "message": "No usable textual output from model after retries",
                "domain": domain,
                "attempts": responses
            }
            debug_path = self._save_debug_failure(debug_payload)
            self.log("error", "No textual output after retries", {"debug_path": debug_path})
            raise RuntimeError(f"LLM returned no usable textual output after retries. See {debug_path} and logs/ollama_raw_response.txt")

        # Parse and save ideas
        ideas = self._parse_text_to_ideas(text_response)
        if not ideas:
            debug_payload = {"raw_text": text_response, "attempts": responses}
            debug_path = self._save_debug_failure(debug_payload)
            raise RuntimeError(f"Failed to parse LLM output into ideas. Raw saved at: {debug_path}")

        self.state.setdefault("ideas", []).extend(ideas)
        self.log("info", "Idea generation complete", {"count": len(ideas)})
        out = {"ideas": ideas, "raw": text_response}
        self.print_terminal(out)
        return out
