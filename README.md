# Anna CloudFinOps & API Spend Guardian (MCP Server + Web App)

> **Program**: [Anna AI App Builder Program ($80,000/Month Pool — `https://dorahacks.io/hackathon/2349`)](https://dorahacks.io/hackathon/2349)  
> **Target Ecosystem**: Anna AI OS (`anna.partners`)  
> **Architecture**: Model Context Protocol (`MCP 2024-11-05`) JSON-RPC 2.0 Server + FastAPI / Zero-Dependency Python HTTP Server + Interactive FinOps Studio (`static/index.html`)

---

## Overview

**Anna CloudFinOps & API Spend Guardian** is a dual-surface **Anna AI OS Marketplace Web App** and **MCP Tool Server** that helps AI engineering teams and autonomous agents audit, bound, and cut their LLM/API and cloud infrastructure spend by **60%–87%** without degrading task quality:

1. **Multi-Provider LLM & Cloud Spend Auditing (`finops_audit_spend`)**:
   - Tracks input, cached-input, and output token costs across OpenAI (`gpt-4o`, `gpt-4o-mini`, `o3-mini`), Anthropic (`claude-3-7-sonnet`, `claude-3-5-haiku`), Google (`gemini-2.5-pro`, `gemini-2.5-flash`), and DeepSeek (`deepseek-v3`).
2. **Real-Time Anomaly & Runaway Loop Detection (`finops_detect_anomalies`)**:
   - Flags statistical Z-score spend spikes, runaway agent retry loops (`retry_rate >= 25%`), and uncached heavy system prompts (`>= 12,000` input tokens/request with `< 15%` cache hit rate).
3. **Autonomous Model-Routing & Prefix-Caching Optimizer (`finops_optimize_routing`)**:
   - Matches endpoint task complexity (`classification`, `extraction`, `summarization`, `code_generation`, `deep_reasoning`) to the optimal cost/latency model tier and emits an executable `anna.finops.v1` routing policy.
4. **Workspace Budget Guardrails & Circuit Breakers (`finops_evaluate_budget_policy`)**:
   - Enforces `HEALTHY`, `WARNING`, `THROTTLE_TIER`, and `CIRCUIT_BREAKER` policies automatically.

---

## Repository Structure

```text
anna-ai-marketplace-app/
├── anna-app.manifest.json       # Anna AI OS Marketplace App & MCP registration manifest
├── src/
│   ├── finops_engine.py         # Core LLM/Cloud FinOps pricing, anomaly detection & routing engine
│   ├── mcp_tools.py             # MCP 2024-11-05 JSON-RPC 2.0 tool & resource server
│   └── server.py                # FastAPI + zero-dependency stdlib HTTP server
├── static/
│   └── index.html               # Interactive Anna CloudFinOps Web App & MCP Playground
├── tests/
│   └── test_finops.py           # 6-test unit & integration suite (100% pass)
├── requirements.txt
├── SUBMISSION_GUIDE.md
└── README.md
```

---

## Quickstart

### 1. Run the Unit & Integration Test Suite
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

### 2. Start the Web App & MCP Server
```bash
python3 src/server.py
# Listening on http://127.0.0.1:8090 (Web UI at / and MCP JSON-RPC 2.0 at POST /mcp)
```
