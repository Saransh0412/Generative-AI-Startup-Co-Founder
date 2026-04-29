# agents/market_agent.py
from .base_agent import BaseAgent
from typing import Optional

class MarketAgent(BaseAgent):
    def __init__(self, name: str, state: dict, callbacks, web_tool: Optional[object] = None):
        super().__init__(name, state, callbacks)
        self.web = web_tool

    def run(self, idea: dict):
        self.log("info", f"Starting market research for: {idea.get('title')}")
        query = f"{idea.get('title')} market India TAM competitors 2025"
        results = []
        try:
            if self.web:
                results = self.web.search(query, num_results=5)
        except Exception as e:
            self.log("info", f"WebTool search failed: {e}")
            results = []

        if not results:
            results = [{"title": f"Placeholder competitor for {idea.get('title')}", "link": "https://example.com", "snippet": "Placeholder"}]

        mr = {
            "market_size_inr": 100_000_000.0,
            "growth_cagr_pct": 18.0,
            "competitors": results,
            "swot": {
                "strengths": ["Strong demand"],
                "weaknesses": ["Regulatory hurdles"],
                "opportunities": ["Tier-2/3 expansion"],
                "threats": ["Established incumbents"]
            },
            "supporting_links": [r.get("link") for r in results]
        }
        iid = idea["id"]
        self.state.setdefault("market_research", {})[iid] = mr
        self.print_terminal({"idea_id": iid, "market_research": mr})
        self.log("info", "Market research saved", {"idea_id": iid})
        return mr
