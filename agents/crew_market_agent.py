# agents/crew_market_agent.py
"""
CrewMarketAgent: Performs market research for a startup idea.
Primary: MCP search API
Fallback: WebTool (DuckDuckGo) → hardcoded domain-aware data
"""
from .base_agent import BaseAgent
from tools.mcp_client import MCPClient
from tools.web_tool import WebTool
from typing import Optional


def _domain_aware_swot(idea: dict) -> dict:
    """Generate a domain-aware SWOT analysis."""
    desc = (idea.get("short_description", "") + " " + idea.get("title", "")).lower()

    strengths = ["Growing digital adoption in India", "Large underserved market"]
    weaknesses = ["High customer acquisition cost", "Regulatory complexity"]
    opportunities = ["Expand to Tier 2/3 cities", "Government digital India push", "Post-COVID digital shift"]
    threats = ["Large incumbents with deep pockets", "Regulatory changes", "Price-sensitive market"]

    if any(kw in desc for kw in ("health", "medical", "symptom", "biofeedback")):
        strengths += ["Rising health awareness post-COVID", "Telemedicine adoption surge"]
        weaknesses += ["Trust barrier for digital health", "CDSCO regulatory hurdles"]
        opportunities += ["ABDM (Ayushman Bharat Digital Mission) integration"]
        threats += ["Established players like Practo, Apollo 247"]

    if any(kw in desc for kw in ("finance", "fintech", "payment", "loan")):
        strengths += ["UPI ecosystem advantage", "High smartphone penetration"]
        weaknesses += ["RBI compliance overhead", "High fraud risk"]
        opportunities += ["MSME credit gap of ₹25 lakh crore"]
        threats += ["PhonePe, Paytm, CRED dominance"]

    if any(kw in desc for kw in ("education", "edtech", "learning")):
        strengths += ["Large student population (500M+)", "NEP 2020 tailwinds"]
        weaknesses += ["Low willingness to pay", "High churn after free trial"]
        opportunities += ["Vernacular content demand", "Skill India initiative"]
        threats += ["BYJU's, Unacademy, PhysicsWallah"]

    if any(kw in desc for kw in ("food", "nutrition", "delivery")):
        strengths += ["Food delivery habit established", "Health-conscious urban consumers"]
        weaknesses += ["Thin margins", "Logistics complexity"]
        opportunities += ["Cloud kitchen model", "D2C nutrition brands"]
        threats += ["Swiggy, Zomato, BigBasket"]

    return {
        "strengths": strengths[:4],
        "weaknesses": weaknesses[:4],
        "opportunities": opportunities[:4],
        "threats": threats[:4],
    }


def _domain_aware_market_size(idea: dict) -> tuple:
    """Return (market_size_inr, cagr_pct) based on domain."""
    desc = (idea.get("short_description", "") + " " + idea.get("title", "")).lower()

    if any(kw in desc for kw in ("health", "medical", "symptom", "biofeedback", "nutrition")):
        return 500_000_000_000, 22.0  # ₹500B, 22% CAGR (Indian digital health)
    if any(kw in desc for kw in ("finance", "fintech", "payment", "loan", "invest")):
        return 1_000_000_000_000, 25.0  # ₹1T, 25% CAGR (Indian fintech)
    if any(kw in desc for kw in ("education", "edtech", "learning", "school")):
        return 400_000_000_000, 20.0  # ₹400B, 20% CAGR (Indian edtech)
    if any(kw in desc for kw in ("food", "nutrition", "delivery", "restaurant")):
        return 750_000_000_000, 18.0  # ₹750B, 18% CAGR (Indian food delivery)
    if any(kw in desc for kw in ("ecommerce", "marketplace", "retail", "shop")):
        return 2_000_000_000_000, 27.0  # ₹2T, 27% CAGR (Indian e-commerce)
    if any(kw in desc for kw in ("agriculture", "agri", "farm", "crop")):
        return 300_000_000_000, 15.0  # ₹300B, 15% CAGR (Indian agritech)

    return 100_000_000_000, 18.0  # Default: ₹100B, 18% CAGR


class CrewMarketAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        state: dict,
        callbacks,
        mcp_base: str = "http://localhost:9000",
        headers: dict = None,
    ):
        super().__init__(name, state, callbacks)
        self.mcp = MCPClient(base_url=mcp_base, headers=headers)
        self.web = WebTool(throttle_seconds=0.5)

    def _search_via_mcp(self, query: str, max_results: int = 5):
        """Try MCP search endpoint."""
        resp = self.mcp.search(query, max_results=max_results)
        results = resp.get("results") or resp.get("data") or resp.get("hits") or []
        return results

    def _search_via_web(self, query: str, num_results: int = 5):
        """Fallback: DuckDuckGo web search."""
        return self.web.search(query, num_results=num_results)

    def _normalize_results(self, results: list) -> list:
        """Normalize search results to a consistent format."""
        normalized = []
        for r in results:
            normalized.append({
                "title": r.get("title") or r.get("name") or "Unknown",
                "link": r.get("link") or r.get("url") or None,
                "snippet": r.get("snippet") or r.get("summary") or "",
            })
        return normalized

    def run(self, idea: dict) -> dict:
        idea_id = idea.get("id")
        title = idea.get("title", "")
        self.log("info", "MarketAgent starting", {"idea_id": idea_id, "title": title})

        query = f"{title} startup competitors India {idea.get('short_description', '')[:80]}"
        normalized = []
        search_source = "none"

        # 1) Try MCP search
        try:
            self.log("info", "Calling MCP.search", {"query": query})
            results = self._search_via_mcp(query, max_results=5)
            if results:
                normalized = self._normalize_results(results)
                search_source = "mcp"
                self.log("info", "MCP search succeeded", {"count": len(normalized)})
        except Exception as mcp_err:
            self.log("error", "MCP search failed, trying WebTool", {"error": str(mcp_err)})

        # 2) Fallback to WebTool
        if not normalized:
            try:
                self.log("info", "Calling WebTool.search", {"query": query})
                results = self._search_via_web(query, num_results=5)
                if results:
                    normalized = self._normalize_results(results)
                    search_source = "web"
                    self.log("info", "WebTool search succeeded", {"count": len(normalized)})
            except Exception as web_err:
                self.log("error", "WebTool search also failed", {"error": str(web_err)})

        # 3) If still empty, use domain-aware placeholder competitors
        if not normalized:
            search_source = "fallback"
            desc = (idea.get("short_description", "") + " " + title).lower()
            if any(kw in desc for kw in ("health", "medical", "symptom")):
                normalized = [
                    {"title": "Practo", "link": "https://practo.com", "snippet": "Online doctor consultation platform"},
                    {"title": "Apollo 247", "link": "https://apollo247.com", "snippet": "Digital health platform"},
                    {"title": "1mg", "link": "https://1mg.com", "snippet": "Online pharmacy and health platform"},
                ]
            elif any(kw in desc for kw in ("finance", "fintech", "payment")):
                normalized = [
                    {"title": "PhonePe", "link": "https://phonepe.com", "snippet": "Digital payments platform"},
                    {"title": "Paytm", "link": "https://paytm.com", "snippet": "Financial services super app"},
                    {"title": "CRED", "link": "https://cred.club", "snippet": "Credit card rewards platform"},
                ]
            elif any(kw in desc for kw in ("education", "edtech", "learning")):
                normalized = [
                    {"title": "BYJU's", "link": "https://byjus.com", "snippet": "Online learning platform"},
                    {"title": "Unacademy", "link": "https://unacademy.com", "snippet": "Live learning platform"},
                    {"title": "PhysicsWallah", "link": "https://pw.live", "snippet": "Affordable online education"},
                ]
            else:
                normalized = [
                    {"title": f"{title} Competitor 1", "link": "https://example.com/c1", "snippet": f"Competitor in {title} space"},
                    {"title": f"{title} Competitor 2", "link": "https://example.com/c2", "snippet": f"Alternative solution for {title}"},
                ]

        # Build market research output
        market_size, cagr = _domain_aware_market_size(idea)
        swot = _domain_aware_swot(idea)

        mr = {
            "market_size_inr": market_size,
            "growth_cagr_pct": cagr,
            "competitors": normalized,
            "swot": swot,
            "supporting_links": [r["link"] for r in normalized if r.get("link")],
            "search_source": search_source,
        }

        # Store and publish A2A message
        self.state.setdefault("market_research", {})[idea_id] = mr
        env = self.make_envelope(
            self.name, "FinanceAgent",
            {"idea_id": idea_id, "market_research": mr}
        )
        self.state.setdefault("a2a_messages", []).append(env)

        self.log("info", "Market research completed", {
            "idea_id": idea_id,
            "source": search_source,
            "competitors": len(normalized),
        })
        self.print_terminal({"idea_id": idea_id, "market_research": mr})
        return mr
