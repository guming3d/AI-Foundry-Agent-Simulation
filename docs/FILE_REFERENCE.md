# File Reference Card

Quick reference for all simulation files.

## 📜 Scripts (What to Run)

| File | Command | Purpose | Time | Output |
|------|---------|---------|------|--------|
| **test_simulation.py** | `python test_simulation.py` | Quick verification (5 calls) | 30s | test_metrics.csv |
| **simulate_agent_operations.py** | `python simulate_agent_operations.py` | Main simulator (100 calls default) | 5-10min | simulation_metrics.csv, simulation_summary.json |
| **visualize_metrics.py** | `python visualize_metrics.py` | Generate dashboard | 10s | metrics_visualization.png |
| **batch_create_agents.py** | `python batch_create_agents.py` | Create agents (already done ✅) | 5-10min | created_agents_results.csv |

## 📚 Documentation (What to Read)

| File | Read If... | Length |
|------|------------|--------|
| **QUICKSTART.md** | First time using the simulator | 5 min read |
| **SUMMARY.md** | Want overview of what was built | 3 min read |
| **README_SIMULATION.md** | Need complete technical details | 15 min read |
| **FILE_REFERENCE.md** | Want quick lookup table (this file) | 1 min read |

## 📊 Data Files (What Gets Created)

| File | Created By | Format | Size | Purpose |
|------|-----------|--------|------|---------|
| **created_agents_results.csv** | batch_create_agents.py | CSV | ~10 KB | List of 108 agents with Azure IDs |
| **simulation_metrics.csv** | simulate_agent_operations.py | CSV | ~50-500 KB | Detailed per-call metrics |
| **simulation_summary.json** | simulate_agent_operations.py | JSON | ~2 KB | Aggregated statistics |
| **metrics_visualization.png** | visualize_metrics.py | PNG | ~200 KB | 6-panel dashboard |

## 🎯 Common Workflows

### First Time Setup
```bash
1. python test_simulation.py                    # Verify (30s)
2. python simulate_agent_operations.py          # Run (10min)
3. python visualize_metrics.py                  # Visualize (10s)
```

### Daily Monitoring
```bash
python simulate_agent_operations.py --num-calls 50 --threads 3
python visualize_metrics.py
```

### Load Testing
```bash
python simulate_agent_operations.py --num-calls 1000 --threads 10 --delay 0.2
python visualize_metrics.py
```

### Overnight Batch
```bash
nohup python simulate_agent_operations.py --num-calls 5000 --threads 15 > log.txt 2>&1 &
# Next morning:
python visualize_metrics.py
```

## 🔧 Key Parameters

### simulate_agent_operations.py

| Parameter | Default | Description | Example |
|-----------|---------|-------------|---------|
| `--num-calls` | 100 | Number of API calls | `--num-calls 500` |
| `--threads` | 5 | Parallel workers | `--threads 10` |
| `--delay` | 0.5 | Seconds between calls | `--delay 0.2` |
| `--agents-csv` | created_agents_results.csv | Input agents file | `--agents-csv my_agents.csv` |
| `--output` | simulation_metrics.csv | Output metrics file | `--output metrics_jan6.csv` |

### visualize_metrics.py

| Parameter | Default | Description | Example |
|-----------|---------|-------------|---------|
| `--input` | simulation_metrics.csv | Input metrics file | `--input metrics_jan6.csv` |

## 📈 Metrics Explanation

### CSV Columns (simulation_metrics.csv)

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `timestamp` | ISO 8601 | When call was made | 2026-01-06T10:30:15.123 |
| `agent_id` | String | Original agent ID | AG001 |
| `agent_name` | String | Full agent name | ORG01-CustomerSupport-AG001 |
| `azure_id` | String | Azure agent ID | ORG01-CustomerSupport-AG001:1 |
| `model` | String | Model used | gpt-4.1-mini |
| `org_id` | String | Organization | ORG01 |
| `agent_type` | String | Agent category | CustomerSupport |
| `query` | String | Input sent to agent | "How do I track my order?" |
| `query_length` | Integer | Query character count | 25 |
| `response_text` | String | Agent response (truncated) | "To track your order..." |
| `response_length` | Integer | Full response chars | 347 |
| `latency_ms` | Float | Response time | 1234.56 |
| `success` | Boolean | Call succeeded | True |
| `error_message` | String | Error if failed | None |

### JSON Fields (simulation_summary.json)

```json
{
  "total_calls": 100,              // Total API calls made
  "successful_calls": 98,          // Succeeded
  "failed_calls": 2,               // Failed
  "success_rate": 98.0,            // Percentage
  "avg_latency_ms": 1567.23,       // Average response time
  "min_latency_ms": 789.45,        // Fastest call
  "max_latency_ms": 4321.10,       // Slowest call
  "agent_type_distribution": {     // Calls per type
    "CustomerSupport": 15,
    "PricingOptimization": 12
  },
  "model_distribution": {          // Calls per model
    "gpt-4.1-mini": 25,
    "grok-4": 20
  }
}
```

## 🎨 Visualization Panels

1. **Success Rate Pie Chart** - Green = success, Red = failed
2. **Latency Histogram** - Distribution of response times, red line = mean
3. **Agent Type Bar Chart** - Which types were called most
4. **Model Bar Chart** - Which models were used most
5. **Latency Box Plot** - Compare model performance
6. **Time Series Scatter** - Latency trend over call sequence

## 🚨 Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | All good! |
| 1 | Error | Check error message |

## 💡 Pro Tips

### Speed Up Simulation
```bash
--threads 20 --delay 0.1  # More parallel, less waiting
```

### Slow Down (Avoid Rate Limits)
```bash
--threads 2 --delay 2.0   # Fewer parallel, more waiting
```

### Process Only Specific Agents
Edit `simulate_agent_operations.py`:
```python
# Filter agents before loading
agents = [a for a in self.agents if a['org_id'] == 'ORG01']
```

### Export for Excel Analysis
```bash
# Already in CSV format!
open simulation_metrics.csv  # macOS
xdg-open simulation_metrics.csv  # Linux
start simulation_metrics.csv  # Windows
```

## 🔍 Quick Grep Commands

```bash
# Find all successful calls
grep ",True," simulation_metrics.csv

# Count failures
grep ",False," simulation_metrics.csv | wc -l

# Find slowest calls (over 3000ms)
awk -F',' '$12 > 3000' simulation_metrics.csv

# Show only CustomerSupport agent calls
grep "CustomerSupport" simulation_metrics.csv

# Extract just latency column
cut -d',' -f12 simulation_metrics.csv | tail -n +2
```

## 📦 Dependencies

```bash
pip install azure-ai-projects azure-identity python-dotenv pandas matplotlib seaborn
```

## 🔐 Authentication

Required for scripts to work:
```bash
az login
az account set --subscription "Your-Subscription"
```

Or set environment variables:
```bash
export AZURE_CLIENT_ID=<id>
export AZURE_CLIENT_SECRET=<secret>
export AZURE_TENANT_ID=<tenant>
```

## 🎯 Decision Tree: Which Script to Run?

```
Need to verify setup?
  └─> python test_simulation.py

Want to generate metrics?
  └─> python simulate_agent_operations.py

Have metrics, need visuals?
  └─> python visualize_metrics.py

Need to create new agents?
  └─> python batch_create_agents.py

Want to modify queries?
  └─> Edit QUERY_TEMPLATES in simulate_agent_operations.py

Need help?
  └─> Read QUICKSTART.md
```

## 📞 Troubleshooting Lookup

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "File not found: created_agents_results.csv" | Agents not created yet | Run batch_create_agents.py |
| "DefaultAzureCredential failed" | Not logged in | Run `az login` |
| Many failures (>10%) | Rate limiting or service issue | Increase `--delay` |
| Slow execution | High delay setting | Reduce `--delay` |
| Out of memory | Too many threads | Reduce `--threads` |
| Import error | Missing dependency | `pip install <package>` |

---

**Quick Start Command:**
```bash
python test_simulation.py && echo "✅ Setup verified! Run: python simulate_agent_operations.py"
```
