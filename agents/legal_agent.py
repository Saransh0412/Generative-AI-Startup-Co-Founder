# agents/legal_agent.py
"""
LegalAgent: Generates legal & compliance requirements for a startup idea.
Uses Ollama LLM for AI-powered generation with a hardcoded fallback.
"""
from .base_agent import BaseAgent
import json
import re
from typing import Optional, Any


def _extract_json_block(text: str) -> Optional[dict]:
    """Try to extract a JSON object from LLM output."""
    if not text:
        return None
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    # Try to find JSON block in markdown code fences
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    # Try to find raw JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return None


def _hardcoded_legal(idea: dict) -> dict:
    """Domain-aware hardcoded fallback for legal compliance."""
    title = idea.get("title", "")
    desc = idea.get("short_description", "").lower()

    licenses = ["Business Registration (LLP/Private Ltd)", "GST Registration", "Shops & Establishment Act"]
    data_actions = [
        "Draft Privacy Policy compliant with IT Act 2000",
        "Implement AES-256 encryption at rest and TLS in transit",
        "Appoint Data Protection Officer (DPO)",
        "Data Processing Agreement with third-party vendors",
        "User consent mechanism for data collection",
    ]
    sector_regs = ["Consumer Protection Act 2019", "Information Technology Act 2000"]
    next_steps = [
        "Consult CA for tax structuring and GST compliance",
        "Engage legal counsel for IP protection and trademark registration",
        "Review sector-specific regulations with compliance expert",
    ]

    # Domain-specific additions
    if any(kw in desc for kw in ("health", "medical", "symptom", "clinic", "patient", "biofeedback")):
        licenses.append("CDSCO Registration (if medical device)")
        sector_regs += [
            "Telemedicine Practice Guidelines 2020",
            "Clinical Establishments Act 2010",
            "DPDP Act 2023 (health data is sensitive)",
        ]
        next_steps.append("Obtain NABH accreditation for clinical operations")

    if any(kw in desc for kw in ("finance", "payment", "loan", "invest", "insurance", "fintech")):
        licenses += ["RBI NBFC License (if lending)", "SEBI Registration (if investment advisory)"]
        sector_regs += ["PMLA 2002 (AML compliance)", "RBI Payment Aggregator Guidelines"]
        next_steps.append("Engage RBI-registered compliance consultant")

    if any(kw in desc for kw in ("food", "nutrition", "restaurant", "delivery", "fssai")):
        licenses.append("FSSAI License")
        sector_regs.append("Food Safety and Standards Act 2006")

    if any(kw in desc for kw in ("education", "edtech", "learning", "school", "student")):
        sector_regs.append("National Education Policy 2020 guidelines")
        next_steps.append("Register with DPIIT for Startup India benefits")

    if any(kw in desc for kw in ("ecommerce", "marketplace", "retail", "shop")):
        sector_regs += ["Consumer Protection (E-Commerce) Rules 2020", "FDI Policy for e-commerce"]

    return {
        "required_licenses": licenses,
        "data_protection_actions": data_actions,
        "sector_regs": sector_regs,
        "next_steps": next_steps,
    }


class LegalAgent(BaseAgent):
    def __init__(self, name: str, state: dict, callbacks, ollama_client=None, model_name: str = "gemma3:4b"):
        super().__init__(name, state, callbacks)
        self.ollama = ollama_client
        self.model = model_name

    def _llm_generate(self, idea: dict) -> Optional[dict]:
        """Ask LLM to generate legal compliance requirements as JSON."""
        if not self.ollama:
            return None

        prompt = (
            "You are a legal compliance expert for Indian startups. "
            "Given the startup idea below, generate a JSON object with EXACTLY these keys:\n"
            "- required_licenses: list of strings (licenses/registrations needed in India)\n"
            "- data_protection_actions: list of strings (DPDP/IT Act compliance steps)\n"
            "- sector_regs: list of strings (sector-specific regulations)\n"
            "- next_steps: list of strings (immediate action items)\n\n"
            f"Startup: {idea.get('title')}\n"
            f"Description: {idea.get('short_description')}\n\n"
            "Return ONLY valid JSON. No explanation, no markdown, no code fences."
        )

        try:
            resp = self.ollama.generate(self.model, prompt, params={"max_tokens": 600, "temperature": 0.1})
            text = resp.get("text", "")
            result = _extract_json_block(text)
            if result and "required_licenses" in result:
                self.log("info", "LLM legal generation succeeded", {"idea_id": idea.get("id")})
                return result
        except Exception as e:
            self.log("error", "LLM legal generation failed", {"error": str(e)})

        return None

    def run(self, idea: dict) -> dict:
        idea_id = idea.get("id")
        self.log("info", f"Starting legal checks for: {idea.get('title')}", {"idea_id": idea_id})

        # Try LLM first, fall back to hardcoded
        lc = self._llm_generate(idea)
        if not lc:
            self.log("info", "Using hardcoded legal fallback", {"idea_id": idea_id})
            lc = _hardcoded_legal(idea)

        self.state.setdefault("legal", {})[idea_id] = lc
        self.print_terminal({"idea_id": idea_id, "legal": lc})
        self.log("info", "Legal checks saved", {"idea_id": idea_id})
        return lc
