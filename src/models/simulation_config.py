"""
Simulation configuration data models for Microsoft Foundry Agent Toolkit.

These models define the structure for simulation and daemon configuration,
including load profiles and execution parameters.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class RangeConfig(BaseModel):
    """Configuration for a numeric range (min/max)."""

    min: float = Field(..., description="Minimum value")
    max: float = Field(..., description="Maximum value")

    def as_int_range(self) -> tuple:
        """Return as integer tuple (min, max)."""
        return (int(self.min), int(self.max))

    def as_float_range(self) -> tuple:
        """Return as float tuple (min, max)."""
        return (self.min, self.max)


class OperationParams(BaseModel):
    """Parameters for operation simulation."""

    num_calls: RangeConfig = Field(..., description="Number of calls range")
    threads: RangeConfig = Field(..., description="Thread count range")
    delay: RangeConfig = Field(..., description="Delay between calls range (seconds)")


class GuardrailParams(BaseModel):
    """Parameters for guardrail testing."""

    num_tests: RangeConfig = Field(..., description="Number of tests range")
    threads: RangeConfig = Field(..., description="Thread count range")
    delay: RangeConfig = Field(..., description="Delay between tests range (seconds)")


class LoadProfile(BaseModel):
    """Load profile configuration for a specific time period."""

    operations: OperationParams = Field(..., description="Operation simulation parameters")
    guardrails: GuardrailParams = Field(..., description="Guardrail testing parameters")


class BusyHoursConfig(BaseModel):
    """Configuration for busy hours schedule."""

    enabled: bool = Field(default=True, description="Whether busy hours are enabled")
    start_hour: int = Field(default=8, description="Start hour (0-23)")
    end_hour: int = Field(default=18, description="End hour (0-23)")
    comment: Optional[str] = Field(None, description="Description of this schedule")


class BusyHoursSchedule(BaseModel):
    """Complete busy hours schedule for week."""

    description: Optional[str] = Field(None, description="Schedule description")
    weekday: BusyHoursConfig = Field(default_factory=BusyHoursConfig, description="Weekday schedule")
    weekend: BusyHoursConfig = Field(
        default_factory=lambda: BusyHoursConfig(start_hour=10, end_hour=16),
        description="Weekend schedule"
    )


class SimulationMix(BaseModel):
    """Configuration for simulation type mix."""

    operations_weight: int = Field(default=70, description="Weight for operations (0-100)")
    guardrails_weight: int = Field(default=30, description="Weight for guardrail tests (0-100)")
    comment: Optional[str] = Field(None, description="Description of mix")

    @property
    def total_weight(self) -> int:
        return self.operations_weight + self.guardrails_weight


class OutputConfig(BaseModel):
    """Configuration for output files and directories."""

    base_dir: str = Field(default="output", description="Base output directory")
    operations_csv: str = Field(default="operations_metrics.csv", description="Operations metrics file")
    guardrails_csv: str = Field(default="guardrail_results.csv", description="Guardrail results file")
    log_file: str = Field(default="simulation.log", description="Log file name")
    daily_summary_dir: str = Field(default="daily_summaries", description="Daily summaries directory")


class ErrorHandlingConfig(BaseModel):
    """Configuration for error handling behavior."""

    max_consecutive_failures: int = Field(default=5, description="Max failures before cooldown")
    failure_cooldown_minutes: int = Field(default=10, description="Cooldown period after max failures")
    retry_on_rate_limit: bool = Field(default=True, description="Whether to retry on rate limits")


class AgentsConfig(BaseModel):
    """Configuration for agent source."""

    csv_path: str = Field(default="created_agents_results.csv", description="Path to agents CSV")


class DaemonConfig(BaseModel):
    """Complete daemon configuration."""

    description: Optional[str] = Field(None, description="Configuration description")
    target_daily_requests: RangeConfig = Field(
        default_factory=lambda: RangeConfig(min=3000, max=5000),
        description="Target daily request range"
    )
    execution_interval_minutes: int = Field(default=15, description="Minutes between executions")
    busy_hours: BusyHoursSchedule = Field(
        default_factory=BusyHoursSchedule,
        description="Busy hours schedule"
    )
    load_profiles: Dict[str, LoadProfile] = Field(
        default_factory=dict,
        description="Load profiles by name (busy, normal, quiet)"
    )
    simulation_mix: SimulationMix = Field(
        default_factory=SimulationMix,
        description="Simulation type mix"
    )
    output: OutputConfig = Field(
        default_factory=OutputConfig,
        description="Output configuration"
    )
    agents: AgentsConfig = Field(
        default_factory=AgentsConfig,
        description="Agent source configuration"
    )
    error_handling: ErrorHandlingConfig = Field(
        default_factory=ErrorHandlingConfig,
        description="Error handling configuration"
    )

    def to_json_dict(self) -> Dict[str, Any]:
        """Convert to JSON-compatible dictionary matching existing format."""
        return {
            "description": self.description or "Configuration for agent simulation daemon",
            "target_daily_requests": {
                "min": int(self.target_daily_requests.min),
                "max": int(self.target_daily_requests.max),
                "comment": "Total requests per day across all simulations"
            },
            "execution_interval_minutes": self.execution_interval_minutes,
            "busy_hours": {
                "description": self.busy_hours.description or "Hours with higher load (business hours)",
                "weekday": {
                    "enabled": self.busy_hours.weekday.enabled,
                    "start_hour": self.busy_hours.weekday.start_hour,
                    "end_hour": self.busy_hours.weekday.end_hour,
                    "comment": self.busy_hours.weekday.comment or f"Monday-Friday {self.busy_hours.weekday.start_hour}AM-{self.busy_hours.weekday.end_hour % 12}PM"
                },
                "weekend": {
                    "enabled": self.busy_hours.weekend.enabled,
                    "start_hour": self.busy_hours.weekend.start_hour,
                    "end_hour": self.busy_hours.weekend.end_hour,
                    "comment": self.busy_hours.weekend.comment or f"Saturday-Sunday {self.busy_hours.weekend.start_hour}AM-{self.busy_hours.weekend.end_hour % 12}PM"
                }
            },
            "load_profiles": {
                name: {
                    "operations": {
                        "num_calls": {"min": int(profile.operations.num_calls.min), "max": int(profile.operations.num_calls.max)},
                        "threads": {"min": int(profile.operations.threads.min), "max": int(profile.operations.threads.max)},
                        "delay": {"min": profile.operations.delay.min, "max": profile.operations.delay.max}
                    },
                    "guardrails": {
                        "num_tests": {"min": int(profile.guardrails.num_tests.min), "max": int(profile.guardrails.num_tests.max)},
                        "threads": {"min": int(profile.guardrails.threads.min), "max": int(profile.guardrails.threads.max)},
                        "delay": {"min": profile.guardrails.delay.min, "max": profile.guardrails.delay.max}
                    }
                }
                for name, profile in self.load_profiles.items()
            },
            "simulation_mix": {
                "operations_weight": self.simulation_mix.operations_weight,
                "guardrails_weight": self.simulation_mix.guardrails_weight,
                "comment": self.simulation_mix.comment or f"{self.simulation_mix.operations_weight}% operations, {self.simulation_mix.guardrails_weight}% guardrail testing"
            },
            "output": {
                "base_dir": self.output.base_dir,
                "operations_csv": self.output.operations_csv,
                "guardrails_csv": self.output.guardrails_csv,
                "log_file": self.output.log_file,
                "daily_summary_dir": self.output.daily_summary_dir
            },
            "agents": {
                "csv_path": self.agents.csv_path
            },
            "error_handling": {
                "max_consecutive_failures": self.error_handling.max_consecutive_failures,
                "failure_cooldown_minutes": self.error_handling.failure_cooldown_minutes,
                "retry_on_rate_limit": self.error_handling.retry_on_rate_limit
            }
        }


class SimulationConfig(BaseModel):
    """Configuration for a single simulation run."""

    agents_csv: str = Field(default="created_agents_results.csv", description="Path to agents CSV")
    num_calls: int = Field(default=100, description="Number of calls to make")
    threads: int = Field(default=5, description="Number of parallel threads")
    delay: float = Field(default=0.5, description="Delay between calls (seconds)")
    output_csv: str = Field(default="simulation_metrics.csv", description="Output metrics file")
    output_summary: str = Field(default="simulation_summary.json", description="Output summary file")

    # Guardrail-specific options
    test_category: Optional[str] = Field(None, description="Specific guardrail category to test")

    def to_cli_args(self, script_type: str = "operations") -> List[str]:
        """Convert to CLI arguments for simulation scripts."""
        args = [
            "--agents-csv", self.agents_csv,
            "--threads", str(self.threads),
            "--delay", str(self.delay),
        ]

        if script_type == "operations":
            args.extend(["--num-calls", str(self.num_calls)])
            args.extend(["--output", self.output_csv])
        elif script_type == "guardrails":
            args.extend(["--num-tests", str(self.num_calls)])
            args.extend(["--output", self.output_csv])
            if self.test_category:
                args.extend(["--category", self.test_category])

        return args
