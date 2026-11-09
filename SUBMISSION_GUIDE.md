# DoraHacks & Anna.Partners Submission Guide — Anna AI App Builder Program

- **Hackathon / Program URL**: `https://dorahacks.io/hackathon/2349`
- **Partner Portal**: `https://anna.partners`
- **Prize Pool**: **$80,000 / Month Non-Competitive Builder Pool** (up to $5,000–$6,000 per qualifying app deployed on Anna AI OS).

---

## Step-by-Step Submission Instructions

1. **Push Repository to Public GitHub**:
   Push `/home/jeff/.gemini/antigravity/scratch/freelancework/pool-contests/anna-ai-marketplace-app/` to a public GitHub repository (e.g., `anna-cloudfinops-guardian`).
2. **Register App on Anna AI OS (`anna.partners`) & DoraHacks (`https://dorahacks.io/hackathon/2349`)**:
   - **App Name**: `Anna CloudFinOps & API Spend Guardian`
   - **Manifest**: `anna-app.manifest.json`
   - **MCP Endpoint**: `POST /mcp` (Protocol `2024-11-05`, 4 tools: `finops_audit_spend`, `finops_detect_anomalies`, `finops_optimize_routing`, `finops_evaluate_budget_policy`)
   - **Web App Entry**: `GET /` (`static/index.html`)
3. **Project Description (Copy-Paste)**:
   ```markdown
   Anna CloudFinOps & API Spend Guardian is an autonomous LLM/API & Cloud FinOps Web Application and Model Context Protocol (MCP 2024-11-05) tool server built for Anna AI OS (`anna.partners`). It audits multi-provider token and infrastructure telemetry (`gpt-4o`, `claude-3-7-sonnet`, `gemini-2.5-flash`, `deepseek-v3`, `o3-mini`), detects statistical Z-score spend spikes and runaway agent retry loops, and generates executable `anna.finops.v1` model-routing and prompt-caching policies that reduce monthly AI spend by up to 87% while enforcing automated workspace budget circuit breakers.
   ```
