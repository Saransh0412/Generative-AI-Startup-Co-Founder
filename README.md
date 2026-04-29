# 🚀 Generative AI Startup Co-Founder

A multi-agent AI system that generates comprehensive startup analysis reports for any domain — powered by local LLMs (Ollama) and MCP (Model Context Protocol).

---

## 📋 What It Does

Given a domain (e.g., "HealthTech"), the system orchestrates 6 specialized AI agents to produce:

| Output | Description |
|--------|-------------|
| 💡 **3 Startup Ideas** | AI-generated ideas with novelty points |
| 📊 **Market Research** | TAM, CAGR, competitors, SWOT analysis |
| 💰 **Financial Model** | 3-year revenue/cost projections, burn rate, runway |
| ⚖️ **Legal Compliance** | Required licenses, data protection, sector regulations |
| 🎤 **Pitch Deck** | 10-slide investor pitch deck |
| 🧭 **Strategy** | Milestones, team plan, go-to-market, KPIs, risk register |

---

## 🏗️ Architecture

```
RunManager (Orchestrator)
├── IdeaAgent          → Ollama LLM (gemma3:4b / deepseek-r1:8b)
├── CrewMarketAgent    → MCP Search → WebTool (DuckDuckGo) → Fallback
├── ADKFinanceAgent    → MCP Compute → Local calculation fallback
├── LegalAgent         → LLM + domain-aware rules
├── PitchAgent         → LLM + state data
└── StrategyAgent      → LLM + domain-aware rules
```

### Agent Communication (A2A)
- Agents share data via `shared_state` (in-memory dict)
- `CrewMarketAgent` publishes market data to `FinanceAgent` via A2A envelopes
- `PitchAgent` and `StrategyAgent` consume market + financial data for richer output

### Fallback Chain
```
MCP Server → WebTool (DuckDuckGo) → Domain-aware hardcoded data
```
The system always produces output even when external services are unavailable.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.ai) installed and running

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Ollama & Pull a Model
```bash
# Start Ollama (if not already running)
ollama serve

# Pull a model (choose one)
ollama pull gemma3:4b        # Recommended (fast, good quality)
ollama pull deepseek-r1:8b   # Better reasoning, slower
ollama pull llama3.2:3b      # Fastest, lighter
```

> **Note:** If any of the above models are not supported or unavailable on your machine, run `ollama list` to see installed models or use the latest available model with `ollama pull <model-name>`. You can find all supported models at [ollama.com/library](https://ollama.com/library).

### 3. (Optional) Start the MCP Mock Server
```bash
python mcp_mock.py
# Runs on http://localhost:9000
```

### 4. Run the Pipeline

**Option A: Streamlit UI (Recommended)**
```bash
streamlit run streamlit_app.py
```
Open http://localhost:8501 in your browser.

**Option B: Command Line**
```bash
python run_main.py --domain "HealthTech" --model-name "gemma3:4b"
```

**Option C: Simple CLI**
```bash
python run_cli.py --domain "FinTech" --model-name "gemma3:4b"
```

**Option D: Debug Mode**
```bash
python debug_run.py
```

---

## 📁 Project Structure

```
New folder/
├── agents/
│   ├── base_agent.py          # BaseAgent, CallbackRegistry
│   ├── idea_agent.py          # LLM-powered idea generation
│   ├── crew_market_agent.py   # Market research (MCP/Web/Fallback)
│   ├── adk_finance_agent.py   # Financial modeling (MCP/Local)
│   ├── legal_agent.py         # Legal compliance (LLM + rules)
│   ├── pitch_agent.py         # Pitch deck generation (LLM + data)
│   ├── strategy_agent.py      # Strategy & roadmap (LLM + rules)
│   ├── market_agent.py        # Legacy market agent (WebTool)
│   └── finance_agent.py       # Legacy finance agent (local calc)
├── tools/
│   ├── ollama_client.py       # Ollama HTTP client (NDJSON streaming)
│   ├── mcp_client.py          # MCP HTTP client (search + compute)
│   ├── web_tool.py            # DuckDuckGo web scraper
│   └── file_tool.py           # JSON/text file utilities
├── models.py                  # Pydantic v2 data models
├── run_manager.py             # Pipeline orchestrator
├── run_main.py                # Main entry point (argparse)
├── run_cli.py                 # Simple CLI runner
├── cli.py                     # Typer CLI
├── debug_run.py               # Debug runner
├── mcp_mock.py                # Flask mock MCP server
├── streamlit_app.py           # Streamlit web UI
├── requirements.txt           # Python dependencies
├── logs/
│   ├── events.log             # Event log (JSON lines)
│   ├── agents.log             # Agent log
│   └── ollama_raw_response.txt # Raw LLM responses
└── outputs/
    ├── final_output.json      # Full structured output
    ├── final_output.md        # Markdown report
    └── debug_*.json           # Debug files (on failure)
```

---

## ⚙️ Configuration

### CLI Options
```
--domain, -d        Domain for startup ideas (required)
--ollama-base       Ollama URL (default: http://localhost:11434)
--model-name        LLM model name (default: gemma3:4b)
--verbose           Print full traceback on error
```

### RunManager Parameters
```python
RunManager(
    ollama_base="http://localhost:11434",
    model_name="gemma3:4b",
    mcp_base="http://localhost:9000",
    mcp_headers=None,  # Optional auth headers for MCP
)
```

---

## 🔌 MCP Mock Server

The `mcp_mock.py` provides two endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /` | GET | Health check |
| `/api/search` | POST | Returns mock competitor search results |
| `/api/compute` | POST | Computes financial model |

```bash
python mcp_mock.py  # Starts on port 9000
```

---

## 📊 Sample Output

```
Domain: HealthTech
Ideas: Smart Symptom Tracker, Remote Biofeedback Coaching, Personalized Nutrition Scanner

Smart Symptom Tracker:
  Market Size: ₹500B | CAGR: 22%
  Year 1 Revenue: ₹3,24,000 | Year 3: ₹4,27,000
  Funding Required: ₹10,000,000
  Licenses: CDSCO, GST, Telemedicine Guidelines
  Pitch Deck: 10 slides generated
  Milestones: 9 milestones (Month 1 → Month 24)
```

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| `LLM returned no usable output` | Check Ollama is running: `ollama serve` |
| `MCP connection refused` | Start mock server: `python mcp_mock.py` |
| `Model not found` | Pull model: `ollama pull gemma3:4b` |
| `Pydantic validation failed` | Non-fatal — output still saved |
| Empty ideas list | Try a different model or increase `max_tokens` |

---

## 📦 Dependencies

```
requests>=2.28.0       # HTTP client
pydantic>=2.0.0        # Data validation (v2)
typer[all]>=0.9.0      # CLI framework
streamlit>=1.20.0      # Web UI
beautifulsoup4>=4.12.2 # Web scraping
python-dotenv>=1.0.0   # Environment variables
rich>=12.0.0           # Terminal formatting
flask>=2.0.0           # MCP mock server
```

---

## 🧪 Testing the System

```bash
# Test imports
python -c "from run_manager import RunManager; print('OK')"

# Test with debug mode (HealthTech domain)
python debug_run.py

# Test MCP mock server
python mcp_mock.py &
curl -X POST http://localhost:9000/api/search -H "Content-Type: application/json" -d '{"q":"healthtech","max_results":3}'
```

---

## 📄 License

MIT License

---

## 👤 Author

**Saransh Bhargava**

- 🎓 Generative AI Course Project
- 💻 Built with Python, Ollama, Streamlit, and multi-agent architecture
- 📧 Feel free to reach out for questions or collaboration

---

*Built with ❤️ using local LLMs and multi-agent AI — no cloud API keys required.*
