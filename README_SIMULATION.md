# AI Foundry Agent Operation Simulator

This toolkit simulates realistic agent operations to generate metrics data for AI Foundry agents.

> Note: This file documents the legacy script workflow. For the new generator app (Textual TUI + Gradio UI),
> start with `README.md`.

## Overview

The simulation system consists of three main components:

1. **Agent Creation** (`batch_create_agents.py`) - Creates agents from CSV configuration
2. **Operation Simulation** (`simulate_agent_operations.py`) - Simulates agent calls with realistic queries
3. **Metrics Visualization** (`visualize_metrics.py`) - Analyzes and visualizes collected metrics

## Prerequisites

```bash
pip install azure-ai-projects azure-identity python-dotenv pandas matplotlib seaborn
```

## Environment Setup

Create a `.env` file with:

```
PROJECT_ENDPOINT=https://foundry-control-plane.services.ai.azure.com/api/projects/foundry-control-plane
```

Ensure Azure credentials are configured via `az login` or environment variables.

## Usage

### Step 1: Create Agents (Already Done)

```bash
python batch_create_agents.py
```

**Output:**
- `created_agents_results.csv` - Successfully created agents with Azure IDs
- `failed_agents_results.csv` - Any failed agent creations

### Step 2: Run Operation Simulation

**Basic Usage:**
```bash
python simulate_agent_operations.py
```

**Advanced Options:**
```bash
python simulate_agent_operations.py \
  --agents-csv created_agents_results.csv \
  --num-calls 500 \
  --threads 10 \
  --delay 0.3 \
  --output simulation_metrics.csv
```

**Parameters:**
- `--agents-csv`: Path to agents CSV (default: `created_agents_results.csv`)
- `--num-calls`: Number of agent calls to simulate (default: 100)
- `--threads`: Parallel threads for simulation (default: 5)
- `--delay`: Delay between calls in seconds (default: 0.5)
- `--output`: Output metrics CSV file (default: `simulation_metrics.csv`)

**Example Scenarios:**

Quick test (10 calls):
```bash
python simulate_agent_operations.py --num-calls 10 --threads 2
```

Medium load (500 calls, 10 parallel threads):
```bash
python simulate_agent_operations.py --num-calls 500 --threads 10 --delay 0.2
```

Heavy load (2000 calls, 20 parallel threads):
```bash
python simulate_agent_operations.py --num-calls 2000 --threads 20 --delay 0.1
```

### Step 3: Visualize Metrics

```bash
python visualize_metrics.py --input simulation_metrics.csv
```

**Generates:**
- `metrics_visualization.png` - Six-panel visualization dashboard
- Console output with detailed statistics

## Query Templates

The simulator generates contextually appropriate queries for each agent type:

| Agent Type | Example Queries |
|-----------|----------------|
| **Customer Support** | "How do I track my order #1234?", "I need to return a product..." |
| **Catalog Enrichment** | "Generate product descriptions for category 5678", "Tag and categorize..." |
| **Pricing Optimization** | "Analyze pricing trends for category X", "Calculate price elasticity..." |
| **Store Ops** | "Check inventory levels for store #42", "Report foot traffic patterns..." |
| **Supply Chain** | "Track shipment status for order #9876", "Optimize delivery routes..." |
| **Fraud Detection** | "Analyze transaction pattern for account #1234", "Review suspicious payment..." |
| **Marketing Copy** | "Generate email campaign for product launch", "Create social media posts..." |
| **HR Assistant** | "What are the PTO policies?", "Help with benefits enrollment..." |
| **Finance Analyst** | "Generate quarterly revenue report", "Analyze budget variance..." |

## Output Files

### simulation_metrics.csv

Detailed metrics for each API call:

| Column | Description |
|--------|-------------|
| `timestamp` | ISO 8601 timestamp of the call |
| `agent_id` | Original agent ID (e.g., AG001) |
| `agent_name` | Full agent name (e.g., ORG01-CustomerSupport-AG001) |
| `azure_id` | Azure agent ID with version |
| `model` | Model used (gpt-4.1-mini, grok-4, etc.) |
| `org_id` | Organization ID (ORG01-ORG12) |
| `agent_type` | Agent type (CustomerSupport, etc.) |
| `query` | The input query sent to agent |
| `query_length` | Character count of query |
| `response_text` | Agent response (truncated to 200 chars) |
| `response_length` | Full response character count |
| `latency_ms` | Response time in milliseconds |
| `success` | Boolean success/failure flag |
| `error_message` | Error details if failed |

### simulation_summary.json

Aggregated statistics:
```json
{
  "total_calls": 100,
  "successful_calls": 98,
  "failed_calls": 2,
  "success_rate": 98.0,
  "avg_latency_ms": 1234.56,
  "min_latency_ms": 567.89,
  "max_latency_ms": 3456.78,
  "agent_type_distribution": {
    "CustomerSupport": 15,
    "PricingOptimization": 12,
    ...
  },
  "model_distribution": {
    "gpt-4.1-mini": 25,
    "grok-4": 20,
    ...
  }
}
```

### metrics_visualization.png

Six-panel dashboard showing:
1. **Success Rate** - Pie chart of successful vs failed calls
2. **Latency Distribution** - Histogram with mean latency line
3. **Calls by Agent Type** - Horizontal bar chart
4. **Calls by Model** - Vertical bar chart
5. **Latency by Model** - Box plot comparison
6. **Latency Over Time** - Scatter plot of call sequence

## Performance Tuning

### Controlling Load

**Light Load (monitoring/testing):**
- `--num-calls 50 --threads 2 --delay 1.0`
- ~50 seconds runtime
- Minimal API load

**Medium Load (realistic simulation):**
- `--num-calls 500 --threads 5 --delay 0.5`
- ~10 minutes runtime
- Balanced load pattern

**Heavy Load (stress testing):**
- `--num-calls 5000 --threads 20 --delay 0.1`
- ~30 minutes runtime
- High concurrent load

### Thread Safety

The simulator is thread-safe with:
- Thread-local API clients
- Lock-protected metrics collection
- Queue-based work distribution

## Troubleshooting

### Authentication Issues
```
Error: DefaultAzureCredential failed
```
**Solution:** Run `az login` or set environment variables:
```bash
export AZURE_CLIENT_ID=<your-client-id>
export AZURE_CLIENT_SECRET=<your-secret>
export AZURE_TENANT_ID=<your-tenant>
```

### Rate Limiting
```
Error: TooManyRequests (429)
```
**Solution:** Increase `--delay` parameter:
```bash
python simulate_agent_operations.py --delay 1.0
```

### Agent Not Found
```
Error: Agent 'ORG01-CustomerSupport-AG001' not found
```
**Solution:** Verify agent exists in created_agents_results.csv or re-run batch creation.

## Data Analysis Examples

### SQL-like Analysis with pandas

```python
import pandas as pd

df = pd.read_csv('simulation_metrics.csv')

# Average latency by organization
org_latency = df[df['success']].groupby('org_id')['latency_ms'].mean()

# Success rate by model
model_success = df.groupby('model')['success'].mean() * 100

# Top 10 slowest queries
slowest = df.nlargest(10, 'latency_ms')[['agent_name', 'query', 'latency_ms']]

# Peak call times
df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
hourly_distribution = df.groupby('hour').size()
```

### Power BI / Excel Integration

Import `simulation_metrics.csv` directly into:
- Microsoft Power BI
- Excel with Power Query
- Tableau
- Any SQL database

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  1. Agent Creation (batch_create_agents.py)             │
│     Input: contoso_ai_control_plane_demo(agents).csv    │
│     Output: created_agents_results.csv                  │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  2. Operation Simulation (simulate_agent_operations.py) │
│     - Random agent selection                            │
│     - Contextual query generation                       │
│     - Parallel API calls with threading                 │
│     - Metrics collection (latency, success, etc.)       │
│     Output: simulation_metrics.csv, summary.json        │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  3. Metrics Visualization (visualize_metrics.py)        │
│     - Statistical analysis                              │
│     - Six-panel dashboard                               │
│     Output: metrics_visualization.png                   │
└─────────────────────────────────────────────────────────┘
```

## Real-World Usage Patterns

### Daily Operations Monitoring
```bash
# Run hourly simulation for baseline metrics
*/60 * * * * cd /path/to/project && python simulate_agent_operations.py --num-calls 100
```

### Load Testing Before Deployment
```bash
# Gradual ramp-up
for calls in 100 500 1000 2000 5000; do
  echo "Testing with $calls calls..."
  python simulate_agent_operations.py --num-calls $calls --threads 10
  sleep 300  # 5 min cooldown
done
```

### A/B Testing Model Performance
```bash
# Create two agent pools with different models
# Run parallel simulations and compare latency metrics
python simulate_agent_operations.py --agents-csv agents_pool_a.csv --output metrics_a.csv &
python simulate_agent_operations.py --agents-csv agents_pool_b.csv --output metrics_b.csv &
wait
python compare_metrics.py metrics_a.csv metrics_b.csv
```

## Contributing

To add new agent types:

1. Add query templates to `QUERY_TEMPLATES` dict in `simulate_agent_operations.py`
2. Update CSV with new agent type rows
3. Run batch creation and simulation

## License

Internal tool for AI Foundry operations testing.
