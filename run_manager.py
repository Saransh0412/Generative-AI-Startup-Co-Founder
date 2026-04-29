# run_manager.py
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from agents.base_agent import CallbackRegistry
from tools.ollama_client import OllamaClient
from agents.base_agent import BaseAgent
from agents.crew_market_agent import CrewMarketAgent
from agents.adk_finance_agent import ADKFinanceAgent

# Optional: import IdeaAgent
try:
    from agents.idea_agent import IdeaAgent
except Exception:
    IdeaAgent = None

# Optional: legal/pitch/strategy agents
try:
    from agents.legal_agent import LegalAgent
except Exception:
    LegalAgent = None

try:
    from agents.pitch_agent import PitchAgent
except Exception:
    PitchAgent = None

try:
    from agents.strategy_agent import StrategyAgent
except Exception:
    StrategyAgent = None

LOGS = Path("logs")
LOGS.mkdir(exist_ok=True)
OUT = Path("outputs")
OUT.mkdir(exist_ok=True)


class RunManager:
    def __init__(
        self,
        ollama_base: str = "http://localhost:11434",
        model_name: str = "gemma3:4b",
        mcp_base: str = "http://localhost:9000",
        mcp_headers: dict = None,
    ):
        self.shared_state = {}
        self.callbacks = CallbackRegistry()

        # Register event logger callback
        def _event_logger(event_name, payload):
            import json, os
            os.makedirs("logs", exist_ok=True)
            with open("logs/events.log", "a", encoding="utf8") as f:
                f.write(json.dumps({"event": event_name, "payload": payload}, default=str) + "\n")

        self.callbacks.register(_event_logger)

        # Create clients / agents
        self.ollama = OllamaClient(base_url=ollama_base)
        self.model_name = model_name

        # IdeaAgent uses Ollama
        if IdeaAgent:
            self.idea_agent = IdeaAgent(
                "IdeaAgent", self.shared_state, self.callbacks,
                self.ollama, model_name=self.model_name
            )
        else:
            self.idea_agent = None

        # MCP-powered agents
        self.market_agent = CrewMarketAgent(
            "MarketAgent", self.shared_state, self.callbacks,
            mcp_base=mcp_base, headers=mcp_headers
        )
        self.finance_agent = ADKFinanceAgent(
            "FinanceAgent", self.shared_state, self.callbacks,
            mcp_base=mcp_base, headers=mcp_headers
        )

        # Optional agents
        self.legal_agent = (
            LegalAgent("LegalAgent", self.shared_state, self.callbacks, self.ollama, model_name=self.model_name)
            if LegalAgent else None
        )
        self.pitch_agent = (
            PitchAgent("PitchAgent", self.shared_state, self.callbacks, self.ollama, model_name=self.model_name)
            if PitchAgent else None
        )
        self.strategy_agent = (
            StrategyAgent("StrategyAgent", self.shared_state, self.callbacks, self.ollama, model_name=self.model_name)
            if StrategyAgent else None
        )

    def run_all(self, domain: str) -> dict:
        ts = datetime.utcnow().isoformat()
        final = {
            "domain": domain,
            "timestamp": ts,
            "ideas": [],
            "market_research": {},
            "financials": {},
            "legal": {},
            "pitch_deck": {},
            "strategy": {},
        }

        # 1) Idea generation
        if self.idea_agent:
            self.callbacks.emit("log", {
                "ts": ts, "agent": "RunManager", "level": "info",
                "message": "Starting IdeaAgent"
            })
            idea_out = self.idea_agent.run(domain)
            ideas = idea_out.get("ideas") if isinstance(idea_out, dict) else None
            if not ideas:
                ideas = self.shared_state.get("ideas") or []
        else:
            # Fallback stub ideas when IdeaAgent not present
            ideas = [
                {
                    "id": "idea_1",
                    "title": "SymptomSync",
                    "short_description": "AI-powered symptom checker integrated with wearables",
                    "novelty_points": ["Wearable integration", "Local language support"],
                },
                {
                    "id": "idea_2",
                    "title": "MindfulMotion",
                    "short_description": "Gamified AR physical therapy",
                    "novelty_points": ["AR guides", "Gamification"],
                },
            ]
            self.shared_state.setdefault("ideas", []).extend(ideas)

        final["ideas"] = ideas

        # 2) For each idea, run Market + Finance + Legal in parallel
        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = {
                ex.submit(self._run_market_finance_legal_for_idea, idea): idea
                for idea in ideas
            }
            for fut in as_completed(futures):
                idea = futures[fut]
                try:
                    fut.result()
                except Exception as e:
                    self.callbacks.emit("log", {
                        "ts": datetime.utcnow().isoformat(),
                        "agent": "RunManager",
                        "level": "error",
                        "message": "Parallel task failed",
                        "payload": {"idea_id": idea.get("id"), "error": str(e)},
                    })

        # Collect outputs from shared_state
        final["market_research"] = self.shared_state.get("market_research", {})
        final["financials"] = self.shared_state.get("financials", {})
        final["legal"] = self.shared_state.get("legal", {})

        # 3) Pitch & Strategy (sequential, after parallel phase)
        if self.pitch_agent:
            try:
                self.pitch_agent.run(ideas)
                final["pitch_deck"] = self.shared_state.get("pitch_deck", {})
            except Exception as e:
                self.callbacks.emit("log", {
                    "ts": datetime.utcnow().isoformat(),
                    "agent": "RunManager",
                    "level": "error",
                    "message": "PitchAgent failed",
                    "payload": {"error": str(e)},
                })

        if self.strategy_agent:
            try:
                self.strategy_agent.run(ideas)
                final["strategy"] = self.shared_state.get("strategy", {})
            except Exception as e:
                self.callbacks.emit("log", {
                    "ts": datetime.utcnow().isoformat(),
                    "agent": "RunManager",
                    "level": "error",
                    "message": "StrategyAgent failed",
                    "payload": {"error": str(e)},
                })

        # 4) Pydantic v2 validation (best-effort)
        try:
            from models import StartupOutput
            try:
                validated = StartupOutput.model_validate(final)
                final = json.loads(validated.model_dump_json())
            except Exception as pe:
                self.callbacks.emit("log", {
                    "ts": datetime.utcnow().isoformat(),
                    "agent": "RunManager",
                    "level": "error",
                    "message": "Pydantic validation failed (non-fatal)",
                    "payload": {"error": str(pe)},
                })
        except Exception:
            pass

        # 5) Save outputs
        final_json_file = OUT / "final_output.json"
        with open(final_json_file, "w", encoding="utf8") as f:
            json.dump(final, f, indent=2, ensure_ascii=False, default=str)

        final_md_file = OUT / "final_output.md"
        self._write_markdown_report(final, domain, final_md_file)

        self.callbacks.emit("log", {
            "ts": datetime.utcnow().isoformat(),
            "agent": "RunManager",
            "level": "info",
            "message": "Run complete",
            "payload": {"json": str(final_json_file), "md": str(final_md_file)},
        })
        return final

    def _write_markdown_report(self, final: dict, domain: str, path):
        """Write a comprehensive Markdown report from the final output."""
        ts = final.get("timestamp", datetime.utcnow().isoformat())
        with open(path, "w", encoding="utf8") as f:
            f.write("# 🚀 Generative AI Startup Co-Founder Report\n\n")
            f.write(f"**Generated:** {ts}  \n")
            f.write(f"**Domain:** {domain}\n\n---\n\n")

            for idea in final.get("ideas", []):
                iid = idea.get("id")
                f.write(f"# 💡 {idea.get('title', 'Untitled')}\n\n")
                f.write(f"_{idea.get('short_description', '')}_\n\n")
                novelty = idea.get("novelty_points", [])
                if novelty:
                    f.write("**Novelty Points:**\n")
                    for n in novelty:
                        f.write(f"- {n}\n")
                    f.write("\n")

                # Market Research
                mr = final.get("market_research", {}).get(iid, {})
                if mr:
                    f.write("## 📊 Market Research\n\n")
                    ms = mr.get("market_size_inr", 0)
                    f.write(f"- **TAM:** ₹{ms:,.0f}\n")
                    f.write(f"- **CAGR:** {mr.get('growth_cagr_pct', 0)}%\n")
                    f.write(f"- **Data Source:** {mr.get('search_source', 'N/A')}\n\n")
                    competitors = mr.get("competitors", [])
                    if competitors:
                        f.write("### Competitors\n")
                        for c in competitors:
                            title_c = c.get("title", "Unknown")
                            snippet = c.get("snippet", "")
                            link = c.get("link")
                            if link:
                                f.write(f"- **[{title_c}]({link})** — {snippet}\n")
                            else:
                                f.write(f"- **{title_c}** — {snippet}\n")
                        f.write("\n")
                    swot = mr.get("swot", {})
                    if swot:
                        f.write("### SWOT Analysis\n")
                        f.write(f"- **Strengths:** {', '.join(swot.get('strengths', []))}\n")
                        f.write(f"- **Weaknesses:** {', '.join(swot.get('weaknesses', []))}\n")
                        f.write(f"- **Opportunities:** {', '.join(swot.get('opportunities', []))}\n")
                        f.write(f"- **Threats:** {', '.join(swot.get('threats', []))}\n\n")

                # Financials
                fin = final.get("financials", {}).get(iid, {})
                if fin:
                    f.write("## 💰 Financial Model\n\n")
                    rev = fin.get("year_wise_revenue_inr", {})
                    costs = fin.get("year_wise_costs_inr", {})
                    f.write("| Year | Revenue (₹) | Costs (₹) | Gross Profit (₹) |\n")
                    f.write("|------|------------|-----------|------------------|\n")
                    for yr in ["year_1", "year_2", "year_3"]:
                        r = rev.get(yr, 0)
                        c = costs.get(yr, 0)
                        p = r - c
                        f.write(f"| {yr.replace('_', ' ').title()} | ₹{r:,.0f} | ₹{c:,.0f} | ₹{p:,.0f} |\n")
                    f.write(f"\n- **Monthly Burn Rate:** ₹{fin.get('burn_rate_monthly_inr', 0):,.0f}\n")
                    f.write(f"- **Runway:** {fin.get('runway_months', 0)} months\n")
                    f.write(f"- **Funding Required:** ₹{fin.get('funding_required_inr', 0):,.0f}\n\n")

                # Legal
                legal = final.get("legal", {}).get(iid, {})
                if legal:
                    f.write("## ⚖️ Legal & Compliance\n\n")
                    f.write("**Required Licenses:**\n")
                    for item in legal.get("required_licenses", []):
                        f.write(f"- {item}\n")
                    f.write("\n**Data Protection Actions:**\n")
                    for item in legal.get("data_protection_actions", []):
                        f.write(f"- {item}\n")
                    f.write("\n**Sector Regulations:**\n")
                    for item in legal.get("sector_regs", []):
                        f.write(f"- {item}\n")
                    f.write("\n**Next Steps:**\n")
                    for item in legal.get("next_steps", []):
                        f.write(f"- {item}\n")
                    f.write("\n")

                # Pitch Deck
                pd = final.get("pitch_deck", {}).get(iid, {})
                if pd:
                    f.write("## 🎤 Pitch Deck\n\n")
                    for slide in pd.get("slides", []):
                        slide_num = slide.get("slide", "")
                        slide_title = slide.get("title", "Slide")
                        slide_content = slide.get("content", "")
                        ai_tag = " 🤖" if slide.get("ai_generated") else ""
                        f.write(f"### Slide {slide_num}: {slide_title}{ai_tag}\n\n")
                        f.write(f"{slide_content}\n\n")

                # Strategy
                strat = final.get("strategy", {}).get(iid, {})
                if strat:
                    f.write("## 🧭 Strategy & Roadmap\n\n")
                    f.write("### Milestones\n")
                    for m in strat.get("milestones", []):
                        f.write(f"- **Month {m.get('month')}** → {m.get('goal', '')}\n")
                    f.write("\n### Team Required\n")
                    for member in strat.get("team_needed", []):
                        f.write(f"- {member}\n")
                    gtm = strat.get("go_to_market", {})
                    if gtm:
                        f.write("\n### Go-To-Market\n")
                        for ch in gtm.get("channels", []):
                            f.write(f"- {ch}\n")
                        budget = gtm.get("cost_monthly_inr")
                        if budget:
                            f.write(f"\n**Monthly Budget:** ₹{budget:,}\n")
                    kpis = strat.get("kpis", [])
                    if kpis:
                        f.write("\n### KPIs\n")
                        for kpi in kpis:
                            f.write(f"- {kpi}\n")
                    risks = strat.get("risks", [])
                    if risks:
                        f.write("\n### Risk Register\n")
                        for r in risks:
                            f.write(f"- **{r.get('risk', '')}** → _{r.get('mitigation', '')}_\n")
                    f.write("\n")

                f.write("\n---\n\n")

    def _run_market_finance_legal_for_idea(self, idea: dict):
        idea_id = idea.get("id")

        # Market
        try:
            self.market_agent.run(idea)
        except Exception as me:
            self.callbacks.emit("log", {
                "ts": datetime.utcnow().isoformat(),
                "agent": "RunManager",
                "level": "error",
                "message": "Market agent error",
                "payload": {"idea_id": idea_id, "error": str(me)},
            })

        # Finance
        try:
            self.finance_agent.run(idea)
        except Exception as fe:
            self.callbacks.emit("log", {
                "ts": datetime.utcnow().isoformat(),
                "agent": "RunManager",
                "level": "error",
                "message": "Finance agent error",
                "payload": {"idea_id": idea_id, "error": str(fe)},
            })

        # Legal
        if self.legal_agent:
            try:
                self.legal_agent.run(idea)
            except Exception as le:
                self.callbacks.emit("log", {
                    "ts": datetime.utcnow().isoformat(),
                    "agent": "RunManager",
                    "level": "error",
                    "message": "Legal agent error",
                    "payload": {"idea_id": idea_id, "error": str(le)},
                })

        return True
