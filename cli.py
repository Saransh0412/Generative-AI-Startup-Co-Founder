# cli.py
import typer
from run_manager import RunManager

app = typer.Typer()

@app.command()   # <-- THIS LINE REGISTERS THE COMMAND
def start(
    domain: str = typer.Option(None, "--domain", "-d", help="Domain to generate ideas for"),
    ollama_base: str = typer.Option("http://localhost:11434", "--ollama-base", help="Ollama base URL"),
    model_name: str = typer.Option("deepseek-r1:8b", "--model-name", help="Model name")
):
    """
    Starts the Generative AI Startup Co-founder pipeline.
    """
    if not domain:
        domain = typer.prompt("Enter domain (e.g. HealthTech)")

    rm = RunManager(ollama_base=ollama_base, model_name=model_name)
    final = rm.run_all(domain)
    typer.secho("Completed. Output saved in outputs/ folder", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app()
