# run_cli.py
import argparse
from run_manager import RunManager

def main():
    parser = argparse.ArgumentParser(description="Run Generative AI Startup Co-founder pipeline (bypass Typer).")
    parser.add_argument("--domain", "-d", required=True, help="Domain to generate ideas for (e.g. HealthTech)")
    parser.add_argument("--ollama-base", default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--model-name", default="deepseek-r1:8b", help="Model name")
    args = parser.parse_args()

    print(f"Starting pipeline for domain: {args.domain}")
    rm = RunManager(ollama_base=args.ollama_base, model_name=args.model_name)
    final = rm.run_all(args.domain)
    print("Pipeline complete. Outputs saved to outputs/final_output.json and outputs/final_output.md")
    # show brief summary
    print("Ideas generated:")
    for idea in final.get("ideas", []):
        print(f" - {idea.get('title')} (id: {idea.get('id')})")

if __name__ == "__main__":
    main()
