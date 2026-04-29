# agents/finance_agent.py
from .base_agent import BaseAgent

class FinanceAgent(BaseAgent):
    def __init__(self, name: str, state: dict, callbacks):
        super().__init__(name, state, callbacks)

    def run(self, idea: dict):
        self.log("info", f"Starting financial modelling for: {idea.get('title')}")
        assumptions = {
            "initial_customers_month1": 200,
            "monthly_growth_pct": 10.0,
            "arpu_monthly_inr": 150.0
        }
        customers = assumptions["initial_customers_month1"]
        revenue = {}
        costs = {}
        for year in [1, 2, 3]:
            customers *= (1 + assumptions["monthly_growth_pct"] / 100) ** 12
            rev = customers * assumptions["arpu_monthly_inr"] * 12
            cost = rev * 0.6
            revenue[f"year_{year}"] = round(rev)
            costs[f"year_{year}"] = round(cost)

        burn = 800_000.0
        runway = (10_000_000.0 / burn) if burn else 0
        funding_required = max(6 * burn, 10_000_000.0)

        fin = {
            "year_wise_revenue_inr": revenue,
            "year_wise_costs_inr": costs,
            "burn_rate_monthly_inr": burn,
            "runway_months": runway,
            "funding_required_inr": funding_required,
            "assumptions": assumptions
        }
        iid = idea["id"]
        self.state.setdefault("financials", {})[iid] = fin
        self.print_terminal({"idea_id": iid, "financials": fin})
        self.log("info", "Financial modelling saved", {"idea_id": iid})
        return fin
