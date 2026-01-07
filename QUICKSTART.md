# Quick Start Guide - Agent Operation Simulator

Get up and running with agent operation simulation in 5 minutes.

> Note: This file documents the legacy script workflow. For the new generator app (Textual TUI + Gradio UI),
> start with `README.md`.

## Prerequisites Check

```bash
# Ensure you're in the right directory
cd /home/minggu/projects_code/control-plane/generate-demo-data

# Verify files exist
ls -la batch_create_agents.py simulate_agent_operations.py visualize_metrics.py

# Check Azure authentication
az account show
```

## Step-by-Step Guide

### 1️⃣ Verify Agent Creation (Already Done ✓)

You've already created 108 agents. Verify the results file exists:

```bash
ls -la created_agents_results.csv
head -5 created_agents_results.csv
```

**Expected output:**
```
agent_id,name,azure_id,version,model,org_id
AG001,ORG01-CustomerSupport-AG001,ORG01-CustomerSupport-AG001:1,1,grok-4-fast-non-reasoning,ORG01
AG002,ORG01-CatalogEnrichment-AG002,ORG01-CatalogEnrichment-AG002:1,1,gpt-5.1-codex,ORG01
...
```

### 2️⃣ Run Quick Test (5 calls)

```bash
python test_simulation.py
```

**What happens:**
- Makes 5 agent API calls
- Tests authentication and connectivity
- Creates `test_metrics.csv` and `simulation_summary.json`
- Takes ~30 seconds

**Expected output:**
```
================================================================================
Running Quick Simulation Test
================================================================================
Loaded 108 agents from created_agents_results.csv
...
✓ Test Completed Successfully!
```

### 3️⃣ Run Full Simulation (100 calls)

```bash
python simulate_agent_operations.py --num-calls 100 --threads 5
```

**What happens:**
- Randomly selects agents and generates contextual queries
- Makes 100 API calls with 5 parallel threads
- Tracks latency, success rate, and response data
- Takes ~5-10 minutes

**Expected output:**
```
================================================================================
Starting Agent Operation Simulation
================================================================================
Total calls to simulate: 100
Parallel threads: 5
...
✓ [ORG01-CustomerSupport-AG001] Query: 'How do I track my order #1234?...' | Latency: 1234ms
✓ [ORG03-PricingOptimization-AG021] Query: 'Analyze pricing trends for...' | Latency: 2156ms
...
================================================================================
Simulation Summary Report
================================================================================
Total API Calls: 100
Successful: 98 (98.0%)
Failed: 2 (2.0%)

Latency Statistics:
  Average: 1567.23ms
  Min: 789.45ms
  Max: 4321.10ms
...
```

### 4️⃣ Visualize Results

```bash
python visualize_metrics.py --input simulation_metrics.csv
```

**What happens:**
- Loads metrics CSV
- Generates statistical analysis
- Creates 6-panel visualization dashboard
- Takes ~10 seconds

**Output files:**
- `metrics_visualization.png` - Visual dashboard
- Console statistics output

**View the visualization:**
```bash
# On Linux with GUI
xdg-open metrics_visualization.png

# On WSL
explorer.exe metrics_visualization.png

# Or copy to a location you can view
cp metrics_visualization.png ~/Desktop/
```

## Common Simulation Scenarios

### Scenario 1: Quick Health Check (10 calls)
```bash
python simulate_agent_operations.py --num-calls 10 --threads 2 --delay 1.0
```
**Use case:** Verify agents are responding, check connectivity
**Time:** ~30 seconds

### Scenario 2: Standard Monitoring (100 calls)
```bash
python simulate_agent_operations.py --num-calls 100 --threads 5 --delay 0.5
```
**Use case:** Daily operations monitoring, baseline metrics
**Time:** ~5-10 minutes

### Scenario 3: Load Testing (1000 calls)
```bash
python simulate_agent_operations.py --num-calls 1000 --threads 10 --delay 0.2
```
**Use case:** Stress testing, capacity planning
**Time:** ~30-45 minutes

### Scenario 4: Overnight Batch (5000 calls)
```bash
nohup python simulate_agent_operations.py --num-calls 5000 --threads 15 --delay 0.1 > simulation.log 2>&1 &
```
**Use case:** Comprehensive data collection, statistical analysis
**Time:** ~2-3 hours
**Monitor:** `tail -f simulation.log`

## Understanding the Output

### simulation_metrics.csv - Detailed Data

Each row represents one API call:

```csv
timestamp,agent_id,agent_name,model,agent_type,query,latency_ms,success
2026-01-06T10:30:15.123,AG001,ORG01-CustomerSupport-AG001,grok-4-fast-non-reasoning,CustomerSupport,"How do I track my order #1234?",1234.56,True
```

**Key columns:**
- `timestamp` - When the call was made
- `agent_name` - Which agent was called
- `model` - Which LLM model processed it
- `agent_type` - Category of agent
- `query` - The input sent
- `latency_ms` - Response time
- `success` - Whether call succeeded

### simulation_summary.json - Aggregated Stats

```json
{
  "total_calls": 100,
  "successful_calls": 98,
  "success_rate": 98.0,
  "avg_latency_ms": 1567.23,
  "agent_type_distribution": {
    "CustomerSupport": 15,
    "PricingOptimization": 12
  },
  "model_distribution": {
    "gpt-4.1-mini": 25,
    "grok-4": 20
  }
}
```

### metrics_visualization.png - Visual Dashboard

Six panels showing:
1. **Success Rate Pie Chart** - Overall reliability
2. **Latency Histogram** - Performance distribution
3. **Agent Type Bar Chart** - Call distribution
4. **Model Bar Chart** - Model usage
5. **Latency Box Plots** - Model comparison
6. **Time Series** - Latency trends

## Analyzing Results

### Find Slowest Agents
```bash
# Sort by latency, show top 10
cat simulation_metrics.csv | grep True | sort -t',' -k12 -rn | head -10 | cut -d',' -f3,8,12
```

### Calculate Success Rate by Model
```python
import pandas as pd
df = pd.read_csv('simulation_metrics.csv')
print(df.groupby('model')['success'].mean() * 100)
```

### Export to Excel
```python
import pandas as pd
df = pd.read_csv('simulation_metrics.csv')
df.to_excel('metrics_report.xlsx', index=False, sheet_name='Agent Metrics')
```

## Troubleshooting

### Problem: Authentication Failed
```
DefaultAzureCredential failed to retrieve a token
```
**Solution:**
```bash
az login
az account set --subscription "Your-Subscription-Name"
```

### Problem: Agent Not Found
```
Agent 'ORG01-CustomerSupport-AG001' not found
```
**Solution:**
- Verify agent exists: `grep "AG001" created_agents_results.csv`
- Check Azure portal for agent status
- Re-run batch creation if needed

### Problem: Rate Limiting (429 errors)
```
TooManyRequests: Rate limit exceeded
```
**Solution:**
```bash
# Increase delay between calls
python simulate_agent_operations.py --num-calls 100 --delay 1.0

# Reduce parallel threads
python simulate_agent_operations.py --num-calls 100 --threads 2
```

### Problem: Slow Performance
```
Taking too long to complete
```
**Solution:**
```bash
# Reduce delay for faster execution (if not rate limited)
python simulate_agent_operations.py --num-calls 100 --delay 0.1 --threads 10
```

## Next Steps

### For Development
1. **Modify Query Templates** - Edit `QUERY_TEMPLATES` in `simulate_agent_operations.py`
2. **Add New Agent Types** - Update CSV and query templates
3. **Custom Metrics** - Extend metrics collection in `call_agent()` method

### For Production
1. **Scheduled Monitoring** - Set up cron jobs for regular simulation
2. **Alerting** - Monitor success rates and latency thresholds
3. **Reporting** - Automate visualization generation and distribution

### For Analysis
1. **Time Series Analysis** - Track metrics over days/weeks
2. **A/B Testing** - Compare model performance
3. **Capacity Planning** - Use load testing results for scaling decisions

## File Reference

| File | Purpose | Output |
|------|---------|--------|
| `batch_create_agents.py` | Create agents from CSV | `created_agents_results.csv` |
| `simulate_agent_operations.py` | Simulate agent calls | `simulation_metrics.csv`, `simulation_summary.json` |
| `visualize_metrics.py` | Generate visualizations | `metrics_visualization.png` |
| `test_simulation.py` | Quick verification test | `test_metrics.csv` |

## Getting Help

- **Detailed Documentation**: See `README_SIMULATION.md`
- **API Reference**: Check Azure AI Projects SDK docs
- **Query Templates**: See `QUERY_TEMPLATES` in `simulate_agent_operations.py`

## One-Liner Commands

```bash
# Complete workflow from scratch
python batch_create_agents.py && python simulate_agent_operations.py --num-calls 100 && python visualize_metrics.py

# Quick test and visualize
python test_simulation.py && python visualize_metrics.py --input test_metrics.csv

# Heavy load test
python simulate_agent_operations.py --num-calls 5000 --threads 20 --delay 0.1 --output heavy_load_metrics.csv
```

---

**Ready to start?** Run the test:
```bash
python test_simulation.py
```
