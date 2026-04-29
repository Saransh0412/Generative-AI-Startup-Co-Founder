# debug_run.py
from run_manager import RunManager
import traceback, json

rm = RunManager()
domain = "HealthTech"
try:
    final = rm.run_all(domain)
    print("Pipeline finished successfully. Outputs saved to outputs/final_output.json")
except Exception as e:
    print("Pipeline raised an exception:")
    traceback.print_exc()
    # save shared_state for inspection
    with open("outputs/debug_shared_state.json", "w", encoding="utf8") as f:
        json.dump(rm.shared_state, f, indent=2, ensure_ascii=False)
    print("Saved rm.shared_state to outputs/debug_shared_state.json")
    print("Check logs/ollama_raw_response.txt and outputs/debug_ollama.json for raw model response.")
