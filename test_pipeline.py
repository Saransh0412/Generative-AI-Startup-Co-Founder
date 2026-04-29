"""
test_pipeline.py - End-to-end pipeline test with stub ideas (no Ollama needed).
Run: python test_pipeline.py
"""
import sys
import json
import os

sys.path.insert(0, ".")

# Patch IdeaAgent to use stub ideas (no Ollama needed)
import agents.idea_agent as ia_mod

def stub_run(self, domain):
    ideas = [
        {
            "id": "idea_test1",
            "title": "SmartHealth AI",
            "short_description": "AI-powered health monitoring app for chronic disease management",
            "novelty_points": ["Real-time monitoring", "Predictive alerts", "Doctor integration"],
        },
        {
            "id": "idea_test2",
            "title": "MediConnect",
            "short_description": "Telemedicine platform connecting rural patients with urban specialists",
            "novelty_points": ["Rural focus", "Vernacular support", "Offline mode"],
        },
        {
            "id": "idea_test3",
            "title": "NutriScan Pro",
            "short_description": "AI nutrition scanner that analyzes food and provides personalized diet plans",
            "novelty_points": ["Camera-based scanning", "Personalized plans", "Wearable integration"],
        },
    ]
    self.state.setdefault("ideas", []).extend(ideas)
    self.log("info", "Stub idea generation complete", {"count": 3})
    return {"ideas": ideas, "raw": "stub"}

ia_mod.IdeaAgent.run = stub_run

# Also patch LegalAgent and StrategyAgent to skip LLM calls (no Ollama)
import agents.legal_agent as la_mod
original_llm_legal = la_mod.LegalAgent._llm_generate
la_mod.LegalAgent._llm_generate = lambda self, idea: None  # Force fallback

import agents.strategy_agent as sa_mod
original_llm_strategy = sa_mod.StrategyAgent._llm_generate
sa_mod.StrategyAgent._llm_generate = lambda self, idea: None  # Force fallback

import agents.pitch_agent as pa_mod
original_llm_pitch = pa_mod.PitchAgent._llm_generate_slide
pa_mod.PitchAgent._llm_generate_slide = lambda self, idea, title, ctx: None  # Force fallback

from run_manager import RunManager

print("=" * 60)
print("  Generative AI Startup Co-Founder - Pipeline Test")
print("=" * 60)
print()
print("Running pipeline with stub ideas (no Ollama required)...")
print()

rm = RunManager(
    ollama_base="http://localhost:11434",
    model_name="gemma3:4b",
    mcp_base="http://localhost:9000",
)

final = rm.run_all("HealthTech")

print()
print("=" * 60)
print("  PIPELINE RESULTS")
print("=" * 60)
print(f"Domain:          {final['domain']}")
print(f"Timestamp:       {final.get('timestamp', 'N/A')}")
print(f"Ideas:           {len(final['ideas'])}")
print(f"Market Reports:  {len(final['market_research'])}")
print(f"Financial Models:{len(final['financials'])}")
print(f"Legal Reports:   {len(final['legal'])}")
print(f"Pitch Decks:     {len(final['pitch_deck'])}")
print(f"Strategies:      {len(final['strategy'])}")
print()

all_ok = True
for idea in final["ideas"]:
    iid = idea["id"]
    title = idea["title"]
    mr = final["market_research"].get(iid, {})
    fin = final["financials"].get(iid, {})
    legal = final["legal"].get(iid, {})
    pd = final["pitch_deck"].get(iid, {})
    strat = final["strategy"].get(iid, {})

    print(f"  [{iid}] {title}")
    print(f"    Market:   TAM=INR{mr.get('market_size_inr', 0):,.0f}, CAGR={mr.get('growth_cagr_pct', 0)}%, "
          f"Competitors={len(mr.get('competitors', []))}, Source={mr.get('search_source', 'N/A')}")
    rev = fin.get("year_wise_revenue_inr", {})
    print(f"    Finance:  Y1=INR{rev.get('year_1', 0):,.0f}, Y3=INR{rev.get('year_3', 0):,.0f}, "
          f"Burn=INR{fin.get('burn_rate_monthly_inr', 0):,.0f}/mo, Runway={fin.get('runway_months', 0)}mo")
    print(f"    Legal:    {len(legal.get('required_licenses', []))} licenses, "
          f"{len(legal.get('sector_regs', []))} regs, {len(legal.get('data_protection_actions', []))} data actions")
    print(f"    Pitch:    {len(pd.get('slides', []))} slides")
    print(f"    Strategy: {len(strat.get('milestones', []))} milestones, "
          f"{len(strat.get('team_needed', []))} team roles, "
          f"{len(strat.get('kpis', []))} KPIs, {len(strat.get('risks', []))} risks")

    # Validate completeness
    checks = [
        ("market_research", bool(mr)),
        ("financials", bool(fin)),
        ("legal", bool(legal)),
        ("pitch_deck", bool(pd)),
        ("strategy", bool(strat)),
        ("slides_count", len(pd.get("slides", [])) == 10),
        ("milestones_count", len(strat.get("milestones", [])) > 0),
        ("competitors", len(mr.get("competitors", [])) > 0),
    ]
    failed = [name for name, ok in checks if not ok]
    if failed:
        print(f"    WARN: Missing data for: {failed}")
        all_ok = False
    else:
        print(f"    OK: All sections complete")
    print()

print()
print("Output files:")
for f in sorted(os.listdir("outputs")):
    size = os.path.getsize(f"outputs/{f}")
    print(f"  outputs/{f} ({size:,} bytes)")

print()
if all_ok:
    print("SUCCESS: Full pipeline completed with all sections populated!")
else:
    print("PARTIAL: Pipeline completed with some warnings (see above)")

print("=" * 60)
