#!/usr/bin/env python3
"""
24/7 Agent Simulation Daemon

Continuously runs agent operations and guardrail testing simulations
with realistic load patterns based on busy/quiet hours.

Usage:
    python simulation_daemon.py [--config CONFIG_FILE]

Signals:
    SIGTERM, SIGINT: Graceful shutdown
"""

import os
import sys
import json
import time
import signal
import random
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import csv


class SimulationDaemon:
    def __init__(self, config_path="simulation_daemon_config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.running = True
        self.consecutive_failures = 0
        self.total_operations_today = 0
        self.total_guardrails_today = 0
        self.current_date = datetime.now().date()
        self.setup_logging()
        self.setup_output_directories()
        self.setup_signal_handlers()

    def load_config(self):
        """Load configuration from JSON file."""
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def setup_logging(self):
        """Setup logging configuration."""
        log_dir = self.config['output']['base_dir']
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, self.config['output']['log_file'])

        # Configure logging to both file and console
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("=" * 80)
        self.logger.info("Simulation Daemon Starting")
        self.logger.info("=" * 80)
        self.logger.info(f"Config file: {self.config_path}")
        self.logger.info(f"Log file: {log_file}")

    def setup_output_directories(self):
        """Create output directories if they don't exist."""
        base_dir = self.config['output']['base_dir']
        summary_dir = os.path.join(base_dir, self.config['output']['daily_summary_dir'])
        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(summary_dir, exist_ok=True)

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False

    def get_load_profile(self):
        """Determine current load profile based on time of day."""
        now = datetime.now()
        hour = now.hour
        is_weekday = now.weekday() < 5  # Monday=0, Sunday=6

        # Check if we're in busy hours
        if is_weekday:
            busy_config = self.config['busy_hours']['weekday']
            if busy_config['enabled']:
                if busy_config['start_hour'] <= hour < busy_config['end_hour']:
                    return 'busy'
        else:  # Weekend
            busy_config = self.config['busy_hours']['weekend']
            if busy_config['enabled']:
                if busy_config['start_hour'] <= hour < busy_config['end_hour']:
                    return 'busy'

        # Determine normal vs quiet hours
        # Quiet hours: 11PM - 6AM
        if hour >= 23 or hour < 6:
            return 'quiet'

        return 'normal'

    def get_random_params(self, profile_name, sim_type):
        """Generate random parameters within configured ranges."""
        profile = self.config['load_profiles'][profile_name][sim_type]

        params = {}
        for param_name, param_range in profile.items():
            if isinstance(param_range, dict) and 'min' in param_range and 'max' in param_range:
                min_val = param_range['min']
                max_val = param_range['max']

                # For float parameters (delay), use uniform distribution
                if isinstance(min_val, float) or isinstance(max_val, float):
                    params[param_name] = round(random.uniform(min_val, max_val), 2)
                else:
                    params[param_name] = random.randint(min_val, max_val)

        return params

    def choose_simulation_type(self):
        """Randomly choose between operations and guardrails based on configured weights."""
        ops_weight = self.config['simulation_mix']['operations_weight']
        guard_weight = self.config['simulation_mix']['guardrails_weight']

        total_weight = ops_weight + guard_weight
        rand_val = random.randint(1, total_weight)

        if rand_val <= ops_weight:
            return 'operations'
        else:
            return 'guardrails'

    def run_operation_simulation(self, params):
        """Run agent operations simulation."""
        self.logger.info(f"Starting OPERATIONS simulation - "
                        f"calls={params['num_calls']}, threads={params['threads']}, delay={params['delay']}")

        output_csv = os.path.join(
            self.config['output']['base_dir'],
            self.config['output']['operations_csv']
        )

        cmd = [
            sys.executable,
            'simulate_agent_operations.py',
            '--agents-csv', self.config['agents']['csv_path'],
            '--num-calls', str(params['num_calls']),
            '--threads', str(params['threads']),
            '--delay', str(params['delay']),
            '--output', output_csv
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            if result.returncode == 0:
                self.logger.info(f"✓ Operations simulation completed successfully ({params['num_calls']} calls)")
                self.total_operations_today += params['num_calls']
                return True
            else:
                self.logger.error(f"✗ Operations simulation failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("✗ Operations simulation timed out")
            return False
        except Exception as e:
            self.logger.error(f"✗ Operations simulation error: {str(e)}")
            return False

    def run_guardrail_simulation(self, params):
        """Run guardrail testing simulation."""
        self.logger.info(f"Starting GUARDRAIL testing - "
                        f"tests={params['num_tests']}, threads={params['threads']}, delay={params['delay']}")

        output_csv = os.path.join(
            self.config['output']['base_dir'],
            self.config['output']['guardrails_csv']
        )

        cmd = [
            sys.executable,
            'simulate_guardrail_testing.py',
            '--agents-csv', self.config['agents']['csv_path'],
            '--num-tests', str(params['num_tests']),
            '--threads', str(params['threads']),
            '--delay', str(params['delay']),
            '--output', output_csv
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            if result.returncode == 0:
                self.logger.info(f"✓ Guardrail testing completed successfully ({params['num_tests']} tests)")
                self.total_guardrails_today += params['num_tests']
                return True
            else:
                self.logger.error(f"✗ Guardrail testing failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("✗ Guardrail testing timed out")
            return False
        except Exception as e:
            self.logger.error(f"✗ Guardrail testing error: {str(e)}")
            return False

    def check_daily_reset(self):
        """Check if we've crossed into a new day and reset counters."""
        current_date = datetime.now().date()
        if current_date != self.current_date:
            # Generate daily summary for yesterday
            self.generate_daily_summary(self.current_date)

            # Reset counters
            self.logger.info(f"New day started: {current_date}")
            self.logger.info(f"Yesterday's totals - Operations: {self.total_operations_today}, "
                           f"Guardrails: {self.total_guardrails_today}")
            self.total_operations_today = 0
            self.total_guardrails_today = 0
            self.current_date = current_date

    def generate_daily_summary(self, date):
        """Generate daily summary report."""
        summary_dir = os.path.join(
            self.config['output']['base_dir'],
            self.config['output']['daily_summary_dir']
        )
        summary_file = os.path.join(summary_dir, f"summary_{date.isoformat()}.json")

        summary = {
            'date': date.isoformat(),
            'total_operations': self.total_operations_today,
            'total_guardrails': self.total_guardrails_today,
            'total_requests': self.total_operations_today + self.total_guardrails_today,
            'target_min': self.config['target_daily_requests']['min'],
            'target_max': self.config['target_daily_requests']['max'],
            'target_met': (
                self.config['target_daily_requests']['min'] <=
                (self.total_operations_today + self.total_guardrails_today) <=
                self.config['target_daily_requests']['max']
            )
        }

        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        self.logger.info(f"Daily summary written to {summary_file}")

    def handle_failure(self):
        """Handle consecutive failures with cooldown."""
        self.consecutive_failures += 1
        max_failures = self.config['error_handling']['max_consecutive_failures']

        if self.consecutive_failures >= max_failures:
            cooldown = self.config['error_handling']['failure_cooldown_minutes']
            self.logger.warning(
                f"Reached {self.consecutive_failures} consecutive failures. "
                f"Entering {cooldown} minute cooldown period."
            )
            time.sleep(cooldown * 60)
            self.consecutive_failures = 0

    def run(self):
        """Main daemon loop."""
        self.logger.info("Daemon is now running. Press Ctrl+C to stop.")
        self.logger.info(f"Target daily requests: {self.config['target_daily_requests']['min']}-"
                        f"{self.config['target_daily_requests']['max']}")
        self.logger.info(f"Execution interval: {self.config['execution_interval_minutes']} minutes")

        while self.running:
            try:
                # Check for daily reset
                self.check_daily_reset()

                # Determine load profile
                load_profile = self.get_load_profile()

                # Choose simulation type
                sim_type = self.choose_simulation_type()

                # Get random parameters
                if sim_type == 'operations':
                    params = self.get_random_params(load_profile, 'operations')
                    params_key = 'num_calls'
                else:
                    params = self.get_random_params(load_profile, 'guardrails')
                    params_key = 'num_tests'

                # Log current status
                now = datetime.now()
                self.logger.info("-" * 80)
                self.logger.info(f"Execution cycle at {now.strftime('%Y-%m-%d %H:%M:%S')}")
                self.logger.info(f"Load profile: {load_profile.upper()}")
                self.logger.info(f"Simulation type: {sim_type.upper()}")
                self.logger.info(f"Today's totals so far - Operations: {self.total_operations_today}, "
                               f"Guardrails: {self.total_guardrails_today}")

                # Run simulation
                if sim_type == 'operations':
                    success = self.run_operation_simulation(params)
                else:
                    success = self.run_guardrail_simulation(params)

                # Handle success/failure
                if success:
                    self.consecutive_failures = 0
                else:
                    self.handle_failure()

                # Wait for next execution
                if self.running:
                    interval_seconds = self.config['execution_interval_minutes'] * 60
                    next_run = datetime.now() + timedelta(seconds=interval_seconds)
                    self.logger.info(f"Next execution scheduled at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                    self.logger.info("-" * 80)

                    # Sleep in small increments to allow for graceful shutdown
                    sleep_remaining = interval_seconds
                    while sleep_remaining > 0 and self.running:
                        sleep_time = min(10, sleep_remaining)  # Check every 10 seconds
                        time.sleep(sleep_time)
                        sleep_remaining -= sleep_time

            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {str(e)}", exc_info=True)
                self.handle_failure()

        # Shutdown
        self.logger.info("Daemon shutdown complete")
        self.logger.info(f"Final today's totals - Operations: {self.total_operations_today}, "
                       f"Guardrails: {self.total_guardrails_today}")


def main():
    parser = argparse.ArgumentParser(description='24/7 Agent Simulation Daemon')
    parser.add_argument('--config', default='simulation_daemon_config.json',
                       help='Path to configuration file')
    args = parser.parse_args()

    # Check if config file exists
    if not os.path.exists(args.config):
        print(f"Error: Configuration file '{args.config}' not found")
        sys.exit(1)

    # Create and run daemon
    daemon = SimulationDaemon(args.config)
    try:
        daemon.run()
    except KeyboardInterrupt:
        daemon.logger.info("Keyboard interrupt received")
    finally:
        # Generate final daily summary
        daemon.generate_daily_summary(daemon.current_date)


if __name__ == '__main__':
    main()
