# mcp_mock.py
from flask import Flask, request, jsonify
from datetime import datetime
import math

app = Flask("mcp-mock")

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})

@app.route("/api/search", methods=["POST"])
def api_search():
    body = request.get_json(force=True, silent=True) or {}
    q = body.get("q", "")
    max_results = int(body.get("max_results", 3) or 3)
    # Return synthetic competitor hits based on query words
    tokens = q.split()
    base = tokens[0] if tokens else "Result"
    results = []
    for i in range(max_results):
        results.append({
            "title": f"{base} Competitor {i+1}",
            "link": f"https://example.com/{base.lower()}-{i+1}",
            "snippet": f"Mock snippet for {q} — competitor {i+1}"
        })
    return jsonify({"results": results})

@app.route("/api/compute", methods=["POST"])
def api_compute():
    body = request.get_json(force=True, silent=True) or {}
    task = body.get("task")
    payload = body.get("payload", {})
    if task == "financial_model":
        assumptions = payload.get("assumptions", {})
        # Basic computation similar to finance_calc.simple_financial_model
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
        funding_required = int(assumptions.get("funding_required_inr", 1000000))
        runway = round(funding_required / burn, 1) if burn else 0
        result = {
            "year_wise_revenue_inr": revenues,
            "year_wise_costs_inr": costs,
            "burn_rate_monthly_inr": burn,
            "runway_months": runway,
            "funding_required_inr": funding_required,
            "assumptions": assumptions
        }
        return jsonify({"result": result})
    else:
        return jsonify({"error": "unknown task", "task": task}), 400

if __name__ == "__main__":
    # Run on port 9000 to match the MCP client default
    app.run(host="0.0.0.0", port=9000, debug=True)
