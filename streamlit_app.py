# streamlit_app.py
"""
Streamlit UI for the Generative AI Startup Co-Founder system.

Run with:
    streamlit run streamlit_app.py
"""
import streamlit as st
import json
import threading
import time
from pathlib import Path
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Startup Co-Founder",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuration")
    st.markdown("---")

    domain = st.text_input(
        "🏢 Domain",
        value="HealthTech",
        placeholder="e.g. HealthTech, FinTech, EdTech",
        help="The industry domain to generate startup ideas for",
    )

    ollama_base = st.text_input(
        "🤖 Ollama Base URL",
        value="http://localhost:11434",
        help="URL of your local Ollama instance",
    )

    model_name = st.selectbox(
        "🧠 LLM Model",
        options=["gemma3:4b", "deepseek-r1:8b", "llama3.2:3b", "mistral:7b", "phi3:mini"],
        index=0,
        help="Local LLM model to use for idea generation",
    )

    mcp_base = st.text_input(
        "🔌 MCP Server URL",
        value="http://localhost:9000",
        help="URL of the MCP mock server (run mcp_mock.py)",
    )

    st.markdown("---")
    st.markdown("### 📋 Quick Start")
    st.markdown(
        "1. Start Ollama: `ollama serve`\n"
        "2. Pull model: `ollama pull gemma3:4b`\n"
        "3. (Optional) Start MCP: `python mcp_mock.py`\n"
        "4. Enter domain & click **Run Pipeline**"
    )

    st.markdown("---")
    st.markdown("### 📁 Output Files")
    out_dir = Path("outputs")
    if out_dir.exists():
        files = list(out_dir.glob("*.json")) + list(out_dir.glob("*.md"))
        if files:
            for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                st.markdown(f"- `{f.name}`")
        else:
            st.markdown("_No outputs yet_")

# ── Main content ──────────────────────────────────────────────────────────────
st.title("🚀 Generative AI Startup Co-Founder")
st.markdown(
    "Generate comprehensive startup analysis including ideas, market research, "
    "financial models, legal compliance, pitch decks, and strategy — all powered by local LLMs."
)

# ── Status area ───────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    run_btn = st.button("▶️ Run Pipeline", type="primary", use_container_width=True)
with col2:
    load_btn = st.button("📂 Load Last Output", use_container_width=True)
with col3:
    clear_btn = st.button("🗑️ Clear Results", use_container_width=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "final_output" not in st.session_state:
    st.session_state.final_output = None
if "running" not in st.session_state:
    st.session_state.running = False
if "log_lines" not in st.session_state:
    st.session_state.log_lines = []

if clear_btn:
    st.session_state.final_output = None
    st.session_state.log_lines = []
    st.rerun()

if load_btn:
    json_file = Path("outputs/final_output.json")
    if json_file.exists():
        with open(json_file, encoding="utf8") as f:
            st.session_state.final_output = json.load(f)
        st.success("✅ Loaded last output from outputs/final_output.json")
    else:
        st.warning("No output file found. Run the pipeline first.")

# ── Run pipeline ──────────────────────────────────────────────────────────────
if run_btn and domain:
    st.session_state.running = True
    st.session_state.log_lines = []
    st.session_state.final_output = None

    progress_bar = st.progress(0, text="Initializing pipeline...")
    log_container = st.empty()
    status_text = st.empty()

    def _run_pipeline():
        try:
            from run_manager import RunManager
            rm = RunManager(
                ollama_base=ollama_base,
                model_name=model_name,
                mcp_base=mcp_base,
            )

            # Monkey-patch callback to capture logs
            original_emit = rm.callbacks.emit
            def _capturing_emit(event_name, payload):
                original_emit(event_name, payload)
                if event_name == "log":
                    msg = payload.get("message", "")
                    agent = payload.get("agent", "")
                    level = payload.get("level", "info")
                    icon = "✅" if level == "info" else "❌"
                    st.session_state.log_lines.append(f"{icon} [{agent}] {msg}")
            rm.callbacks.emit = _capturing_emit

            final = rm.run_all(domain)
            st.session_state.final_output = final
        except Exception as e:
            st.session_state.log_lines.append(f"❌ [Pipeline] FAILED: {e}")
        finally:
            st.session_state.running = False

    thread = threading.Thread(target=_run_pipeline, daemon=True)
    thread.start()

    # Poll for completion
    steps = [
        (10, "🧠 Generating startup ideas with LLM..."),
        (30, "🔍 Running market research..."),
        (50, "💰 Building financial models..."),
        (65, "⚖️ Checking legal compliance..."),
        (80, "🎤 Creating pitch decks..."),
        (90, "🧭 Generating strategy..."),
        (95, "📝 Writing output files..."),
    ]
    step_idx = 0

    while thread.is_alive():
        if step_idx < len(steps):
            pct, msg = steps[step_idx]
            progress_bar.progress(pct, text=msg)
            step_idx += 1
        log_container.text_area(
            "📋 Live Logs",
            value="\n".join(st.session_state.log_lines[-20:]),
            height=200,
        )
        time.sleep(2)

    thread.join()
    progress_bar.progress(100, text="✅ Pipeline complete!")
    log_container.text_area(
        "📋 Live Logs",
        value="\n".join(st.session_state.log_lines[-30:]),
        height=200,
    )

    if st.session_state.final_output:
        status_text.success("🎉 Pipeline completed successfully!")
    else:
        status_text.error("❌ Pipeline failed. Check logs above.")

    st.session_state.running = False
    st.rerun()

# ── Display results ───────────────────────────────────────────────────────────
final = st.session_state.final_output

if final:
    st.markdown("---")
    st.markdown(f"## 📊 Results for Domain: **{final.get('domain', 'Unknown')}**")
    ts = final.get("timestamp", "")
    if ts:
        st.caption(f"Generated: {ts}")

    ideas = final.get("ideas", [])
    if not ideas:
        st.warning("No ideas found in output.")
    else:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💡 Ideas Generated", len(ideas))
        with col2:
            mr_count = len(final.get("market_research", {}))
            st.metric("📊 Market Reports", mr_count)
        with col3:
            fin_count = len(final.get("financials", {}))
            st.metric("💰 Financial Models", fin_count)
        with col4:
            legal_count = len(final.get("legal", {}))
            st.metric("⚖️ Legal Reports", legal_count)

        st.markdown("---")

        # Tabs for each idea
        tab_labels = [f"💡 {idea.get('title', f'Idea {i+1}')}" for i, idea in enumerate(ideas)]
        tabs = st.tabs(tab_labels)

        for tab, idea in zip(tabs, ideas):
            idea_id = idea.get("id")
            with tab:
                st.markdown(f"### {idea.get('title')}")
                st.markdown(f"_{idea.get('short_description')}_")

                novelty = idea.get("novelty_points", [])
                if novelty:
                    st.markdown("**✨ Novelty Points:**")
                    for n in novelty:
                        st.markdown(f"- {n}")

                st.markdown("---")

                # Sub-tabs for each section
                sec_tabs = st.tabs(["📊 Market", "💰 Finance", "⚖️ Legal", "🎤 Pitch Deck", "🧭 Strategy"])

                # ── Market Research ──
                with sec_tabs[0]:
                    mr = final.get("market_research", {}).get(idea_id)
                    if mr:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            ms = mr.get("market_size_inr", 0)
                            st.metric("TAM (INR)", f"₹{ms/1e9:.1f}B" if ms >= 1e9 else f"₹{ms/1e6:.1f}M")
                        with col2:
                            st.metric("CAGR", f"{mr.get('growth_cagr_pct', 0)}%")
                        with col3:
                            src = mr.get("search_source", "unknown")
                            st.metric("Data Source", src.upper())

                        # Competitors
                        competitors = mr.get("competitors", [])
                        if competitors:
                            st.markdown("#### 🏢 Competitors")
                            for c in competitors:
                                link = c.get("link")
                                title_c = c.get("title", "Unknown")
                                snippet = c.get("snippet", "")
                                if link:
                                    st.markdown(f"- **[{title_c}]({link})** — {snippet}")
                                else:
                                    st.markdown(f"- **{title_c}** — {snippet}")

                        # SWOT
                        swot = mr.get("swot", {})
                        if swot:
                            st.markdown("#### 🔄 SWOT Analysis")
                            sc1, sc2 = st.columns(2)
                            with sc1:
                                st.markdown("**💪 Strengths**")
                                for s in swot.get("strengths", []):
                                    st.markdown(f"- {s}")
                                st.markdown("**🎯 Opportunities**")
                                for o in swot.get("opportunities", []):
                                    st.markdown(f"- {o}")
                            with sc2:
                                st.markdown("**⚠️ Weaknesses**")
                                for w in swot.get("weaknesses", []):
                                    st.markdown(f"- {w}")
                                st.markdown("**🚨 Threats**")
                                for t in swot.get("threats", []):
                                    st.markdown(f"- {t}")
                    else:
                        st.info("No market research data available for this idea.")

                # ── Financials ──
                with sec_tabs[1]:
                    fin = final.get("financials", {}).get(idea_id)
                    if fin:
                        # Revenue chart data
                        rev = fin.get("year_wise_revenue_inr", {})
                        costs = fin.get("year_wise_costs_inr", {})

                        fc1, fc2, fc3 = st.columns(3)
                        with fc1:
                            burn = fin.get("burn_rate_monthly_inr", 0)
                            st.metric("Monthly Burn", f"₹{burn:,.0f}")
                        with fc2:
                            runway = fin.get("runway_months", 0)
                            st.metric("Runway", f"{runway} months")
                        with fc3:
                            funding = fin.get("funding_required_inr", 0)
                            st.metric("Funding Required", f"₹{funding/1e6:.1f}M")

                        # Revenue vs Costs table
                        st.markdown("#### 📈 3-Year Projections")
                        table_data = []
                        for yr in ["year_1", "year_2", "year_3"]:
                            r = rev.get(yr, 0)
                            c = costs.get(yr, 0)
                            profit = r - c
                            table_data.append({
                                "Year": yr.replace("_", " ").title(),
                                "Revenue (₹)": f"₹{r:,.0f}",
                                "Costs (₹)": f"₹{c:,.0f}",
                                "Gross Profit (₹)": f"₹{profit:,.0f}",
                                "Margin": f"{(profit/r*100):.1f}%" if r else "N/A",
                            })
                        st.table(table_data)

                        # Assumptions
                        assumptions = fin.get("assumptions", {})
                        if assumptions:
                            st.markdown("#### 🔢 Key Assumptions")
                            for k, v in assumptions.items():
                                if k != "idea_id":
                                    st.markdown(f"- **{k.replace('_', ' ').title()}:** {v}")
                    else:
                        st.info("No financial data available for this idea.")

                # ── Legal ──
                with sec_tabs[2]:
                    legal = final.get("legal", {}).get(idea_id)
                    if legal:
                        lc1, lc2 = st.columns(2)
                        with lc1:
                            st.markdown("#### 📜 Required Licenses")
                            for item in legal.get("required_licenses", []):
                                st.markdown(f"- {item}")

                            st.markdown("#### 🏛️ Sector Regulations")
                            for item in legal.get("sector_regs", []):
                                st.markdown(f"- {item}")

                        with lc2:
                            st.markdown("#### 🔒 Data Protection Actions")
                            for item in legal.get("data_protection_actions", []):
                                st.markdown(f"- {item}")

                            st.markdown("#### ✅ Next Steps")
                            for item in legal.get("next_steps", []):
                                st.markdown(f"- {item}")
                    else:
                        st.info("No legal data available for this idea.")

                # ── Pitch Deck ──
                with sec_tabs[3]:
                    pd = final.get("pitch_deck", {}).get(idea_id)
                    if pd:
                        slides = pd.get("slides", [])
                        st.markdown(f"**{len(slides)} slides generated**")
                        for slide in slides:
                            slide_num = slide.get("slide", "")
                            slide_title = slide.get("title", "Slide")
                            slide_content = slide.get("content", "")
                            ai_gen = slide.get("ai_generated", False)
                            label = f"{'🤖 ' if ai_gen else ''}Slide {slide_num}: {slide_title}"
                            with st.expander(label):
                                st.markdown(slide_content)
                    else:
                        st.info("No pitch deck data available for this idea.")

                # ── Strategy ──
                with sec_tabs[4]:
                    strat = final.get("strategy", {}).get(idea_id)
                    if strat:
                        # Milestones
                        milestones = strat.get("milestones", [])
                        if milestones:
                            st.markdown("#### 🗓️ Milestones")
                            for m in milestones:
                                month = m.get("month", "?")
                                goal = m.get("goal", "")
                                st.markdown(f"- **Month {month}** → {goal}")

                        sc1, sc2 = st.columns(2)
                        with sc1:
                            # Team
                            team = strat.get("team_needed", [])
                            if team:
                                st.markdown("#### 👥 Team Required")
                                for member in team:
                                    st.markdown(f"- {member}")

                            # KPIs
                            kpis = strat.get("kpis", [])
                            if kpis:
                                st.markdown("#### 📏 Key Metrics (KPIs)")
                                for kpi in kpis:
                                    st.markdown(f"- {kpi}")

                        with sc2:
                            # GTM
                            gtm = strat.get("go_to_market", {})
                            if gtm:
                                st.markdown("#### 🎯 Go-To-Market")
                                channels = gtm.get("channels", [])
                                for ch in channels:
                                    st.markdown(f"- {ch}")
                                budget = gtm.get("cost_monthly_inr")
                                if budget:
                                    st.markdown(f"\n**Monthly Budget:** ₹{budget:,}")
                                pricing = gtm.get("pricing_strategy")
                                if pricing:
                                    st.markdown(f"**Pricing:** {pricing}")

                            # Risks
                            risks = strat.get("risks", [])
                            if risks:
                                st.markdown("#### ⚠️ Risk Register")
                                for r in risks:
                                    risk = r.get("risk", "")
                                    mitigation = r.get("mitigation", "")
                                    st.markdown(f"- **{risk}** → _{mitigation}_")
                    else:
                        st.info("No strategy data available for this idea.")

    # ── Download buttons ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📥 Download Reports")
    dl1, dl2 = st.columns(2)

    with dl1:
        json_str = json.dumps(final, indent=2, ensure_ascii=False, default=str)
        st.download_button(
            label="⬇️ Download JSON Report",
            data=json_str,
            file_name=f"startup_report_{final.get('domain', 'output')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )

    with dl2:
        # Build markdown report
        md_file = Path("outputs/final_output.md")
        if md_file.exists():
            md_content = md_file.read_text(encoding="utf8")
            st.download_button(
                label="⬇️ Download Markdown Report",
                data=md_content,
                file_name=f"startup_report_{final.get('domain', 'output')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                use_container_width=True,
            )

elif not run_btn:
    # Welcome screen
    st.markdown("---")
    st.info(
        "👈 Configure your settings in the sidebar, then click **▶️ Run Pipeline** to generate your startup analysis report."
    )

    st.markdown("### 🏗️ System Architecture")
    st.markdown(
        """
        | Agent | Role | Technology |
        |-------|------|------------|
        | **IdeaAgent** | Generates 3 startup ideas | Ollama LLM |
        | **MarketAgent** | Market research & SWOT | MCP Search / WebTool |
        | **FinanceAgent** | 3-year financial model | MCP Compute / Local |
        | **LegalAgent** | Compliance requirements | LLM + Domain rules |
        | **PitchAgent** | 10-slide pitch deck | LLM + State data |
        | **StrategyAgent** | Roadmap & GTM plan | LLM + Domain rules |
        """
    )

    st.markdown("### 📊 Sample Domains")
    sample_domains = ["HealthTech", "FinTech", "EdTech", "AgriTech", "CleanTech", "RetailTech", "LegalTech"]
    cols = st.columns(len(sample_domains))
    for col, d in zip(cols, sample_domains):
        col.markdown(f"- {d}")
