"""verify_output.py - Verify the final output JSON is complete."""
import json

with open("outputs/final_output.json", encoding="utf8") as f:
    data = json.load(f)

print("Keys:", list(data.keys()))
print("Ideas:", len(data["ideas"]))
print("Market:", len(data["market_research"]))
print("Finance:", len(data["financials"]))
print("Legal:", len(data["legal"]))
print("Pitch:", len(data["pitch_deck"]))
print("Strategy:", len(data["strategy"]))
print()

for iid, pd in data["pitch_deck"].items():
    slides = pd.get("slides", [])
    print(f"Pitch {iid}: {len(slides)} slides")
    for s in slides[:3]:
        slide_num = s.get("slide", "?")
        slide_title = s.get("title", "?")
        content_preview = str(s.get("content", ""))[:60]
        print(f"  Slide {slide_num}: {slide_title} - {content_preview}...")

print()
for iid, strat in data["strategy"].items():
    milestones = strat.get("milestones", [])
    team = strat.get("team_needed", [])
    kpis = strat.get("kpis", [])
    risks = strat.get("risks", [])
    print(f"Strategy {iid}: {len(milestones)} milestones, {len(team)} team, {len(kpis)} KPIs, {len(risks)} risks")

print()
print("Output JSON size:", len(json.dumps(data)), "chars")
print("All sections populated:", all([
    len(data["ideas"]) > 0,
    len(data["market_research"]) > 0,
    len(data["financials"]) > 0,
    len(data["legal"]) > 0,
    len(data["pitch_deck"]) > 0,
    len(data["strategy"]) > 0,
]))
