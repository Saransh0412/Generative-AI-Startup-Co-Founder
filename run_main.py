# run_main.py
"""
Unified main runner for the Generative AI Startup Co-Founder pipeline.

Usage:
    python run_main.py --domain "HealthTech" --model-name "gemma3:4b" --ollama-base "http://localhost:11434"

This script:
 - Calls RunManager to run the full agent pipeline
 - Saves outputs/final_output.json and outputs/final_output.md
 - On error, saves debug files under outputs/ and logs/
"""

import argparse
import json
import traceback
from pathlib import Path
from datetime import datetime

# Import your orchestrator (must exist in project)
from run_manager import RunManager

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def save_debug_state(rm: RunManager, exc: Exception = None):
    """Save debug info on failure."""
    debug_state_file = OUTPUT_DIR / "debug_shared_state.json"
    try:
        with open(debug_state_file, "w", encoding="utf8") as f:
            json.dump(getattr(rm, "shared_state", {}), f, indent=2, ensure_ascii=False, default=str)
    except Exception:
        # best-effort
        pass

    if exc:
        debug_exc_file = OUTPUT_DIR / "debug_last_exception.txt"
        with open(debug_exc_file, "w", encoding="utf8") as f:
            f.write("Exception:\n")
            f.write(str(exc) + "\n\n")
            f.write("Traceback:\n")
            f.write(traceback.format_exc())

    return debug_state_file


def write_final_files(final: dict, domain: str):
    """
    Write final JSON and a rich Markdown report containing all agent outputs.
    """
    ts_str = final.get("timestamp", datetime.utcnow().isoformat())
    final_json_file = OUTPUT_DIR / "final_output.json"
    with open(final_json_file, "w", encoding="utf8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False, default=str)

    final_md_file = OUTPUT_DIR / "final_output.md"
    with open(final_md_file, "w", encoding="utf8") as f:
        f.write("# Final Startup Co-Founder Report\n\n")
        f.write(f"Generated on: **{ts_str}**\n\n")
        f.write(f"Domain: **{domain}**\n\n")
        f.write("---\n")

        # Loop through each idea (preserve order if present)
        ideas = final.get("ideas", [])
        if not ideas:
            f.write("_No ideas found in final output._\n")
        for idea in ideas:
            idea_id = idea.get("id")
            f.write(f"\n# 🚀 {idea.get('title','Untitled')}\n")
            f.write(f"### {idea.get('short_description','')}\n\n")

            # MARKET RESEARCH
            mr = final.get("market_research", {}).get(idea_id) or final.get("market_research", {}).get(idea.get("title"))
            if mr:
                f.write("## 📊 Market Research\n")
                f.write(f"- **Market Size (INR):** {mr.get('market_size_inr')}\n")
                f.write(f"- **CAGR:** {mr.get('growth_cagr_pct')}%\n\n")
                f.write("### Competitors\n")
                for c in mr.get("competitors", []):
                    title = c.get("title") or "Unknown"
                    snippet = c.get("snippet") or ""
                    f.write(f"- **{title}** — {snippet}\n")
                    if c.get("link"):
                        f.write(f"  - 🔗 {c['link']}\n")
                sw = mr.get("swot", {})
                if sw:
                    f.write("\n### SWOT Analysis\n")
                    f.write(f"- **Strengths:** {', '.join(sw.get('strengths', []))}\n")
                    f.write(f"- **Weaknesses:** {', '.join(sw.get('weaknesses', []))}\n")
                    f.write(f"- **Opportunities:** {', '.join(sw.get('opportunities', []))}\n")
                    f.write(f"- **Threats:** {', '.join(sw.get('threats', []))}\n\n")

            # FINANCIALS
            fin = final.get("financials", {}).get(idea_id) or final.get("financials", {}).get(idea.get("title"))
            if fin:
                f.write("## 💰 Financial Model\n")
                f.write("### Revenue (INR)\n")
                for year, value in fin.get("year_wise_revenue_inr", {}).items():
                    f.write(f"- **{year}**: ₹{value}\n")
                f.write("\n### Costs (INR)\n")
                for year, value in fin.get("year_wise_costs_inr", {}).items():
                    f.write(f"- **{year}**: ₹{value}\n")
                burn = fin.get("burn_rate_monthly_inr")
                if burn is not None:
                    f.write(f"\n- **Burn Rate:** ₹{burn:,} / month\n")
                runway = fin.get("runway_months")
                if runway is not None:
                    f.write(f"- **Runway:** {runway} months\n")
                req = fin.get("funding_required_inr")
                if req is not None:
                    f.write(f"- **Funding Required:** ₹{req:,}\n\n")
                f.write("### Key Financial Assumptions\n")
                for k, v in fin.get("assumptions", {}).items():
                    f.write(f"- **{k}**: {v}\n")
                f.write("\n")

            # LEGAL
            legal = final.get("legal", {}).get(idea_id) or final.get("legal", {}).get(idea.get("title"))
            if legal:
                f.write("## ⚖️ Legal & Compliance\n")
                f.write("### Required Licenses\n")
                for item in legal.get("required_licenses", []):
                    f.write(f"- {item}\n")
                f.write("\n### Data Protection Requirements\n")
                for item in legal.get("data_protection_actions", []):
                    f.write(f"- {item}\n")
                f.write("\n### Sector Regulations\n")
                for item in legal.get("sector_regs", []):
                    f.write(f"- {item}\n")
                f.write("\n### Next Steps\n")
                for item in legal.get("next_steps", []):
                    f.write(f"- {item}\n")
                f.write("\n")

            # PITCH DECK
            pd = final.get("pitch_deck", {}).get(idea_id) or final.get("pitch_deck", {}).get(idea.get("title"))
            if pd:
                f.write("## 🎤 Pitch Deck (Auto-Generated Slides)\n")
                for slide in pd.get("slides", []):
                    stitle = slide.get("title") or "Slide"
                    scontent = slide.get("content") or ""
                    f.write(f"### 👉 {stitle}\n")
                    f.write(f"{scontent}\n\n")

            # STRATEGY
            strat = final.get("strategy", {}).get(idea_id) or final.get("strategy", {}).get(idea.get("title"))
            if strat:
                f.write("## 🧭 Strategy & Roadmap\n")
                f.write("### Milestones\n")
                for m in strat.get("milestones", []):
                    month = m.get("month")
                    goal = m.get("goal") or m.get("description") or ""
                    f.write(f"- **Month {month}** → {goal}\n")
                f.write("\n### Team Required\n")
                for member in strat.get("team_needed", []):
                    f.write(f"- {member}\n")
                f.write("\n### Go-To-Market Plan\n")
                gtm = strat.get("go_to_market", {})
                channels = gtm.get("channels", [])
                f.write(f"- **Channels:** {', '.join(channels)}\n")
                if gtm.get("cost_monthly_inr") is not None:
                    f.write(f"- **Monthly Budget (INR):** ₹{gtm.get('cost_monthly_inr'):,}\n\n")

            f.write("\n---\n")

    # finished
    print(f"✔ JSON written to: {final_json_file}")
    print(f"✔ Markdown written to: {final_md_file}")

    return final_json_file, final_md_file


def run_pipeline(domain: str, ollama_base: str, model_name: str, verbose: bool = False):
    print("\n========== Generative AI Startup Co-Founder ==========")
    print(f"Domain: {domain}")
    print("Starting full pipeline...\n")

    rm = RunManager(ollama_base=ollama_base, model_name=model_name)

    try:
        final = rm.run_all(domain)
        # ensure timestamp present
        if "timestamp" not in final:
            final["timestamp"] = datetime.utcnow().isoformat()
        # write outputs
        json_file, md_file = write_final_files(final, domain)
        print("✔ Pipeline completed successfully!")
        print(f"✔ JSON: {json_file}")
        print(f"✔ Markdown: {md_file}")
        print("\n=======================================================\n")
        return 0

    except Exception as e:
        print("❌ Pipeline failed — saved debug info.")
        debug_file = save_debug_state(rm, exc=e)
        print(f"Debug saved at: {debug_file}")
        print(f"Last error: {e}")
        if verbose:
            traceback.print_exc()
        print("Check logs/ollama_raw_response.txt and outputs/debug_ollama.json for raw responses.")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Run the Generative AI Startup Co-Founder pipeline.")
    parser.add_argument("--domain", "-d", required=True, help="Domain for startup idea generation")
    parser.add_argument("--ollama-base", default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--model-name", default="gemma3:4b", help="Local LLM model name")
    parser.add_argument("--verbose", action="store_true", help="Print traceback on error")
    args = parser.parse_args()

    exit_code = run_pipeline(domain=args.domain, ollama_base=args.ollama_base, model_name=args.model_name, verbose=args.verbose)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
