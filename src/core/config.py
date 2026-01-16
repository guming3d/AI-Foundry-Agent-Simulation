"""
Centralized configuration for file paths and directories.
"""
from pathlib import Path

# Base directories
RESULTS_DIR = Path("results")
AGENTS_RESULTS_DIR = RESULTS_DIR / "agents"
SIMULATIONS_RESULTS_DIR = RESULTS_DIR / "simulations"
EVALUATIONS_RESULTS_DIR = RESULTS_DIR / "evaluations"
OUTPUT_DIR = Path("output")
GENERATED_CODE_DIR = OUTPUT_DIR / "generated_code"

# Agent result files
CREATED_AGENTS_CSV = AGENTS_RESULTS_DIR / "created_agents_results.csv"
FAILED_AGENTS_CSV = AGENTS_RESULTS_DIR / "failed_agents_results.csv"

# Simulation result files
SIMULATION_METRICS_CSV = SIMULATIONS_RESULTS_DIR / "simulation_metrics.csv"
SIMULATION_SUMMARY_JSON = SIMULATIONS_RESULTS_DIR / "simulation_summary.json"
GUARDRAILS_RESULTS_CSV = SIMULATIONS_RESULTS_DIR / "guardrail_test_results.csv"
GUARDRAILS_SUMMARY_JSON = SIMULATIONS_RESULTS_DIR / "guardrail_security_report.json"


def ensure_directories():
    """Create all necessary output directories if they don't exist."""
    AGENTS_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SIMULATIONS_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    EVALUATIONS_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_CODE_DIR.mkdir(parents=True, exist_ok=True)
