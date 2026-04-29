# agents/adk_finance_agent.py
from .base_agent import BaseAgent
from tools.mcp_client import MCPClient
import math

class ADKFinanceAgent(BaseAgent):
    def __init__(self, name, state, callbacks, mcp_base: str = "http://localhost:9000", headers: dict = None):
        super().__init__(name, state, callbacks)
        self.mcp = MCPClient(base_url=mcp_base, headers=headers)

    def _local_fallback(self, idea_id: str, assumptions: dict):
        ic = int(assumptions.get("initial_customers_month1", 100))
        g = float(assumptions.get("monthly_growth_pct", 10.0)) / 100.0
        arpu = float(assumptions.get("arpu_monthly_inr", 150.0))
        revenues = {}
        costs = {}
        customers = ic
        for y in range(1,4):
            year_rev = 0
            year_cost = 0
            for m in range(12):
                month_rev = customers * arpu
                month_cost = month_rev * 0.6
                year_rev += month_rev
                year_cost += month_cost
                customers = math.floor(customers * (1+g))
            revenues[f"year_{y}"] = round(year_rev)
            costs[f"year_{y}"] = round(year_cost)
        burn = round(costs["year_1"]/12) if costs["year_1"] else 0
        funding = int(assumptions.get("funding_required_inr", 1_000_000))
        runway = round(funding / burn, 1) if burn else 0
        return {
            "year_wise_revenue_inr": revenues,
            "year_wise_costs_inr": costs,
            "burn_rate_monthly_inr": burn,
            "runway_months": runway,
            "funding_required_inr": funding,
            "assumptions": assumptions
        }

    def run(self, idea: dict):
        idea_id = idea.get("id")
        self.log("info", "FinanceAgent starting", {"idea_id": idea_id})
        try:
            # get A2A messages relevant to this idea
            msgs = self.state.get("a2a_messages", [])
            market_info = None
            for m in msgs:
                if m.get("to") in (self.name, "FinanceAgent") and m.get("payload", {}).get("idea_id") == idea_id:
                    market_info = m["payload"].get("market_research")
                    break

            assumptions = {
                "idea_id": idea_id,
                "initial_customers_month1": 200,
                "monthly_growth_pct": 10.0,
                "arpu_monthly_inr": 150.0,
                "funding_required_inr": 10_000_000
            }
            if market_info:
                # optionally adjust assumptions based on market_size
                ms = market_info.get("market_size_inr")
                if ms and ms > 200_000_000:
                    assumptions["initial_customers_month1"] = int(assumptions["initial_customers_month1"] * 1.5)

            # Ask MCP to compute
            try:
                self.log("info", "Calling MCP.compute", {"task": "financial_model", "idea_id": idea_id})
                resp = self.mcp.compute("financial_model", {"assumptions": assumptions})
                fin = resp.get("result") or resp.get("data") or resp
            except Exception as e:
                self.log("error", "MCP.compute failed, using fallback", {"error": str(e)})
                fin = None

            # Validate shape, fallback if necessary
            if not fin or "year_wise_revenue_inr" not in fin:
                fin = self._local_fallback(idea_id, assumptions)

            self.state.setdefault("financials", {})[idea_id] = fin
            self.log("info", "Financial modeling complete", {"idea_id": idea_id})
            self.print_terminal({"idea_id": idea_id, "financials": fin})
            return fin
        except Exception as e:
            self.log("error", "FinanceAgent failed", {"error": str(e)})
            raise
