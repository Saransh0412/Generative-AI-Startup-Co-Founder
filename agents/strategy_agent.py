# agents/strategy_agent.py
"""
StrategyAgent: Generates go-to-market strategy, milestones, and team plan.
Uses Ollama LLM for AI-powered generation with a structured fallback.
"""
from .base_agent import BaseAgent
from typing import List, Optional
import json
import re


def _extract_json_block(text: str) -> Optional[dict]:
    """Try to extract a JSON object from LLM output."""
    if not text:
        return None
    try:
        parsed = json.loads(text.strip())
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return None


def _build_strategy_from_state(idea: dict, state: dict) -> dict:
    """Build a rich strategy using available state data."""
    idea_id = idea.get("id")
    title = idea.get("title", "")
    desc = idea.get("short_description", "").lower()

    mr = state.get("market_research", {}).get(idea_id, {})
    fin = state.get("financials", {}).get(idea_id, {})

    cagr = mr.get("growth_cagr_pct", 18.0)
    market_size = mr.get("market_size_inr", 100_000_000)
    funding = fin.get("funding_required_inr", 10_000_000)
    burn = fin.get("burn_rate_monthly_inr", 800_000)

    # Domain-specific team composition
    team = ["CEO / Co-Founder (1)", "CTO / Tech Lead (1)", "Backend Engineer (2)", "Sales & BD (2)"]
    if any(kw in desc for kw in ("health", "medical", "clinic", "biofeedback")):
        team += ["Medical Advisor (1)", "Regulatory Compliance Officer (1)"]
    if any(kw in desc for kw in ("finance", "fintech", "payment", "loan")):
        team += ["Finance Compliance Officer (1)", "Risk Analyst (1)"]
    if any(kw in desc for kw in ("ai", "ml", "model", "predict", "recommend")):
        team += ["ML Engineer (1)", "Data Scientist (1)"]
    if any(kw in desc for kw in ("food", "nutrition", "delivery")):
        team += ["Operations Manager (1)", "Supply Chain Lead (1)"]

    # GTM channels based on domain
    channels = ["Direct B2B sales", "Digital marketing (Google/Meta ads)", "Content marketing & SEO"]
    if any(kw in desc for kw in ("health", "medical", "clinic")):
        channels += ["Hospital/clinic partnerships", "Doctor referral network"]
    if any(kw in desc for kw in ("education", "edtech", "learning")):
        channels += ["School/college partnerships", "EdTech platform integrations"]
    if any(kw in desc for kw in ("ecommerce", "marketplace", "retail")):
        channels += ["Marketplace listings (Amazon, Flipkart)", "Influencer marketing"]

    monthly_marketing_budget = max(int(burn * 0.3), 100_000)

    milestones = [
        {"month": 1, "goal": "Incorporate company (LLP/Pvt Ltd), complete legal setup"},
        {"month": 2, "goal": "MVP development complete, internal testing"},
        {"month": 3, "goal": "Pilot launch with 10 beta customers, gather feedback"},
        {"month": 4, "goal": "Product iteration based on pilot feedback"},
        {"month": 6, "goal": "100 paying customers, ₹{:,.0f} MRR".format(
            fin.get("assumptions", {}).get("arpu_monthly_inr", 150) * 100
        )},
        {"month": 9, "goal": "1,000 customers, Series A preparation"},
        {"month": 12, "goal": "₹{:,.0f} ARR, expand to 3 cities".format(
            fin.get("year_wise_revenue_inr", {}).get("year_1", 0)
        )},
        {"month": 18, "goal": "Series A close, team expansion to 20+"},
        {"month": 24, "goal": "Pan-India presence, 10,000+ customers"},
    ]

    return {
        "milestones": milestones,
        "team_needed": team,
        "go_to_market": {
            "channels": channels,
            "cost_monthly_inr": monthly_marketing_budget,
            "target_market": "India (Tier 1 & 2 cities initially)",
            "pricing_strategy": "Freemium → Paid subscription",
            "customer_acquisition_cost_inr": max(int(monthly_marketing_budget / 50), 500),
        },
        "kpis": [
            "Monthly Active Users (MAU)",
            "Monthly Recurring Revenue (MRR)",
            "Customer Acquisition Cost (CAC)",
            "Lifetime Value (LTV)",
            "Churn Rate",
            "Net Promoter Score (NPS)",
        ],
        "risks": [
            {"risk": "Regulatory changes", "mitigation": "Proactive compliance monitoring"},
            {"risk": "Low user adoption", "mitigation": "Freemium model + referral incentives"},
            {"risk": "Competition from incumbents", "mitigation": "Focus on niche differentiation"},
            {"risk": "Funding gap", "mitigation": "Bootstrap to revenue, then raise"},
        ],
    }


class StrategyAgent(BaseAgent):
    def __init__(self, name: str, state: dict, callbacks, ollama_client=None, model_name: str = "gemma3:4b"):
        super().__init__(name, state, callbacks)
        self.ollama = ollama_client
        self.model = model_name

    def _llm_generate(self, idea: dict) -> Optional[dict]:
        """Ask LLM to generate strategy as JSON."""
        if not self.ollama:
            return None

        prompt = (
            "You are a startup strategy consultant. For the startup idea below, generate a JSON object with:\n"
            "- milestones: list of {month: int, goal: string} objects (12-month roadmap)\n"
            "- team_needed: list of strings (roles needed)\n"
            "- go_to_market: {channels: list, cost_monthly_inr: int, pricing_strategy: string}\n"
            "- kpis: list of strings (key metrics to track)\n\n"
            f"Startup: {idea.get('title')}\n"
            f"Description: {idea.get('short_description')}\n\n"
            "Return ONLY valid JSON. No explanation, no markdown, no code fences."
        )

        try:
            resp = self.ollama.generate(self.model, prompt, params={"max_tokens": 800, "temperature": 0.2})
            text = resp.get("text", "")
            result = _extract_json_block(text)
            if result and "milestones" in result:
                self.log("info", "LLM strategy generation succeeded", {"idea_id": idea.get("id")})
                return result
        except Exception as e:
            self.log("error", "LLM strategy generation failed", {"error": str(e)})

        return None

    def run(self, ideas: List[dict]) -> dict:
        self.log("info", f"Creating strategy for {len(ideas)} ideas")
        strategies = {}

        for idea in ideas:
            iid = idea.get("id")
            self.log("info", f"Generating strategy for: {idea.get('title')}", {"idea_id": iid})

            # Try LLM first, fall back to data-driven hardcoded
            strategy = self._llm_generate(idea)
            if not strategy:
                self.log("info", "Using data-driven strategy fallback", {"idea_id": iid})
                strategy = _build_strategy_from_state(idea, self.state)

            strategies[iid] = strategy

        self.state.setdefault("strategy", {}).update(strategies)
        self.print_terminal({"strategy_ids": list(strategies.keys())})
        self.log("info", "Strategy created", {"count": len(strategies)})
        return strategies
