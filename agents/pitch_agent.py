# agents/pitch_agent.py
"""
PitchAgent: Generates a 10-slide pitch deck for each startup idea.
Uses Ollama LLM for AI-powered content with a structured fallback.
"""
from .base_agent import BaseAgent
from typing import List, Optional
import json
import re


def _extract_json_block(text: str) -> Optional[list]:
    """Try to extract a JSON array from LLM output."""
    if not text:
        return None
    try:
        parsed = json.loads(text.strip())
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "slides" in parsed:
            return parsed["slides"]
    except Exception:
        pass
    # Try markdown code fence
    match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    # Try raw array
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
    return None


def _build_slides_from_state(idea: dict, state: dict) -> List[dict]:
    """Build rich pitch deck slides using available state data."""
    idea_id = idea.get("id")
    title = idea.get("title", "Untitled")
    desc = idea.get("short_description", "")
    novelty = idea.get("novelty_points", [])

    mr = state.get("market_research", {}).get(idea_id, {})
    fin = state.get("financials", {}).get(idea_id, {})
    legal = state.get("legal", {}).get(idea_id, {})

    # Market data
    market_size = mr.get("market_size_inr", 0)
    cagr = mr.get("growth_cagr_pct", 0)
    competitors = mr.get("competitors", [])
    swot = mr.get("swot", {})

    # Financial data
    rev = fin.get("year_wise_revenue_inr", {})
    burn = fin.get("burn_rate_monthly_inr", 0)
    runway = fin.get("runway_months", 0)
    funding = fin.get("funding_required_inr", 0)
    assumptions = fin.get("assumptions", {})

    # Team from legal next steps
    team_hints = legal.get("next_steps", [])

    competitor_names = ", ".join(
        c.get("title", "Unknown") for c in competitors[:3]
    ) if competitors else "No direct competitors identified"

    rev_y1 = rev.get("year_1", 0)
    rev_y2 = rev.get("year_2", 0)
    rev_y3 = rev.get("year_3", 0)

    slides = [
        {
            "slide": 1,
            "title": "Cover",
            "content": f"**{title}**\n\nYour AI-powered startup co-founder report\n\n_{desc}_",
        },
        {
            "slide": 2,
            "title": "Problem",
            "content": (
                f"The market lacks an efficient solution for: **{title}**\n\n"
                f"Key pain points addressed:\n"
                + "\n".join(f"- {n}" for n in novelty[:3])
                if novelty else f"Core problem: {desc}"
            ),
        },
        {
            "slide": 3,
            "title": "Solution",
            "content": (
                f"**{title}** — {desc}\n\n"
                "Key differentiators:\n"
                + "\n".join(f"- {n}" for n in novelty)
                if novelty else desc
            ),
        },
        {
            "slide": 4,
            "title": "Market Opportunity",
            "content": (
                f"**Total Addressable Market (TAM):** ₹{market_size:,.0f}\n"
                f"**Growth Rate (CAGR):** {cagr}%\n\n"
                f"**SWOT Strengths:** {', '.join(swot.get('strengths', ['High demand']))}\n"
                f"**Opportunities:** {', '.join(swot.get('opportunities', ['Tier-2/3 expansion']))}"
            ),
        },
        {
            "slide": 5,
            "title": "Business Model",
            "content": (
                f"**Revenue Model:** Subscription / SaaS\n"
                f"**ARPU:** ₹{assumptions.get('arpu_monthly_inr', 150)}/month\n"
                f"**Initial Customers (Month 1):** {assumptions.get('initial_customers_month1', 200)}\n"
                f"**Monthly Growth Rate:** {assumptions.get('monthly_growth_pct', 10)}%"
            ),
        },
        {
            "slide": 6,
            "title": "Go-To-Market Strategy",
            "content": (
                "**Phase 1 (0–3 months):** MVP launch, pilot with early adopters\n"
                "**Phase 2 (3–6 months):** B2B partnerships, digital marketing\n"
                "**Phase 3 (6–12 months):** Scale to Tier-2/3 cities, referral programs\n\n"
                "**Channels:** Direct sales, digital ads, partnerships, content marketing"
            ),
        },
        {
            "slide": 7,
            "title": "Competitive Landscape",
            "content": (
                f"**Key Competitors:** {competitor_names}\n\n"
                f"**Our Advantages:**\n"
                f"- {', '.join(swot.get('strengths', ['Innovative approach']))}\n\n"
                f"**Threats to mitigate:**\n"
                f"- {', '.join(swot.get('threats', ['Established incumbents']))}"
            ),
        },
        {
            "slide": 8,
            "title": "Team",
            "content": (
                "**Core Team Required:**\n"
                "- CEO / Founder (domain expert)\n"
                "- CTO (AI/ML + backend)\n"
                "- Product Manager\n"
                "- Sales & Marketing Lead\n"
                "- 2× Backend Engineers\n\n"
                "**Advisors:** Legal, Finance, Domain Expert"
            ),
        },
        {
            "slide": 9,
            "title": "Financial Projections",
            "content": (
                f"**Year 1 Revenue:** ₹{rev_y1:,.0f}\n"
                f"**Year 2 Revenue:** ₹{rev_y2:,.0f}\n"
                f"**Year 3 Revenue:** ₹{rev_y3:,.0f}\n\n"
                f"**Monthly Burn Rate:** ₹{burn:,.0f}\n"
                f"**Runway:** {runway} months\n"
                f"**Funding Required:** ₹{funding:,.0f}"
            ),
        },
        {
            "slide": 10,
            "title": "The Ask",
            "content": (
                f"**Seeking:** ₹{funding:,.0f} in Seed Funding\n\n"
                "**Use of Funds:**\n"
                "- 40% — Product development & engineering\n"
                "- 30% — Sales & marketing\n"
                "- 20% — Operations & compliance\n"
                "- 10% — Working capital\n\n"
                f"**Expected Runway:** {runway} months to Series A"
            ),
        },
    ]
    return slides


class PitchAgent(BaseAgent):
    def __init__(self, name: str, state: dict, callbacks, ollama_client=None, model_name: str = "gemma3:4b"):
        super().__init__(name, state, callbacks)
        self.ollama = ollama_client
        self.model = model_name

    def _llm_generate_slide(self, idea: dict, slide_title: str, context: str) -> Optional[str]:
        """Ask LLM to generate content for a specific slide."""
        if not self.ollama:
            return None

        prompt = (
            f"You are a startup pitch deck expert. Write compelling content for the '{slide_title}' slide "
            f"of a pitch deck for this startup:\n\n"
            f"Startup: {idea.get('title')}\n"
            f"Description: {idea.get('short_description')}\n"
            f"Context data: {context}\n\n"
            f"Write 3-5 bullet points or a short paragraph for the '{slide_title}' slide. "
            "Be specific, data-driven, and investor-focused. Keep it under 100 words."
        )

        try:
            resp = self.ollama.generate(self.model, prompt, params={"max_tokens": 200, "temperature": 0.3})
            text = resp.get("text", "").strip()
            if text and len(text) > 20:
                return text
        except Exception as e:
            self.log("error", f"LLM slide generation failed for {slide_title}", {"error": str(e)})

        return None

    def run(self, ideas: List[dict]) -> dict:
        self.log("info", f"Building pitch decks for {len(ideas)} ideas")
        decks = {}

        for idea in ideas:
            idea_id = idea.get("id")
            self.log("info", f"Building pitch deck for: {idea.get('title')}", {"idea_id": idea_id})

            # Build data-rich slides from shared state
            slides = _build_slides_from_state(idea, self.state)

            # Optionally enhance key slides with LLM
            if self.ollama:
                for i, slide in enumerate(slides):
                    if slide["title"] in ("Problem", "Solution", "Go-To-Market Strategy"):
                        enhanced = self._llm_generate_slide(
                            idea,
                            slide["title"],
                            slide["content"][:300]
                        )
                        if enhanced:
                            slides[i]["content"] = enhanced
                            slides[i]["ai_generated"] = True

            decks[idea_id] = {"slides": slides}

        self.state.setdefault("pitch_deck", {}).update(decks)
        self.print_terminal({"pitch_deck_ids": list(decks.keys())})
        self.log("info", "Pitch decks created", {"count": len(decks)})
        return decks
