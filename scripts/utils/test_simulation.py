#!/usr/bin/env python3
"""
Quick test script to verify the simulation setup.
Runs a small test with 5 agent calls.
"""
import os
import sys
from simulate_agent_operations import AgentSimulator

def test_simulation():
    """Run a quick test with 5 calls."""
    print("=" * 80)
    print("Running Quick Simulation Test")
    print("=" * 80)
    print("This will make 5 agent calls to verify the setup.\n")

    # Check if agents CSV exists
    agents_csv = 'created_agents_results.csv'
    if not os.path.exists(agents_csv):
        print(f"✗ Error: {agents_csv} not found.")
        print("Please run batch_create_agents.py first.")
        sys.exit(1)

    try:
        # Initialize simulator
        simulator = AgentSimulator(agents_csv)

        # Run small test
        simulator.run_simulation(
            num_calls=5,
            parallel_threads=2,
            delay_between_calls=1.0
        )

        # Save results
        simulator.save_metrics('test_metrics.csv')
        simulator.generate_summary_report()

        print("\n" + "=" * 80)
        print("✓ Test Completed Successfully!")
        print("=" * 80)
        print("\nFiles created:")
        print("  - test_metrics.csv")
        print("  - simulation_summary.json")
        print("\nYou can now run the full simulation:")
        print("  python simulate_agent_operations.py --num-calls 100")
        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n✗ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_simulation()
