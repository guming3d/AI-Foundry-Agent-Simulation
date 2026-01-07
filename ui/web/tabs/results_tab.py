"""
Results tab for the Gradio Web UI.

Displays simulation results and statistics.
"""

import gradio as gr
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from ui.shared.state_manager import get_state


def create_results_tab():
    """Create the results tab components."""

    def load_operations_results():
        """Load operations results and create visualizations."""
        state = get_state()
        summary = state.operation_summary

        if not summary:
            return (
                "No operations results available. Run a simulation first.",
                None,
                None,
                [],
                [],
            )

        total = summary.get("total_calls", 0)
        success = summary.get("successful_calls", 0)
        failed = summary.get("failed_calls", 0)
        success_rate = summary.get("success_rate", 0)
        avg_latency = summary.get("avg_latency_ms", 0)
        min_latency = summary.get("min_latency_ms", 0)
        max_latency = summary.get("max_latency_ms", 0)

        summary_text = f"""## Operations Summary

**Total Calls:** {total}
**Successful:** {success} ({success_rate:.1f}%)
**Failed:** {failed}

### Latency
- **Average:** {avg_latency:.2f}ms
- **Min:** {min_latency:.2f}ms
- **Max:** {max_latency:.2f}ms
"""

        # Success rate pie chart
        success_fig = px.pie(
            values=[success, failed],
            names=["Successful", "Failed"],
            title="Success Rate",
            color_discrete_sequence=["#28a745", "#dc3545"],
        )

        # Agent type distribution
        type_dist = summary.get("agent_type_distribution", {})
        if type_dist:
            type_fig = px.bar(
                x=list(type_dist.keys()),
                y=list(type_dist.values()),
                title="Calls by Agent Type",
                labels={"x": "Agent Type", "y": "Calls"},
            )
        else:
            type_fig = None

        # Types table
        types_data = []
        for agent_type, count in sorted(type_dist.items(), key=lambda x: x[1], reverse=True):
            pct = count / total * 100 if total > 0 else 0
            types_data.append([agent_type, count, f"{pct:.1f}%"])

        # Models table
        model_dist = summary.get("model_distribution", {})
        models_data = []
        for model, count in sorted(model_dist.items(), key=lambda x: x[1], reverse=True):
            pct = count / total * 100 if total > 0 else 0
            models_data.append([model, count, f"{pct:.1f}%"])

        return summary_text, success_fig, type_fig, types_data, models_data

    def load_guardrails_results():
        """Load guardrails results and create visualizations."""
        state = get_state()
        summary = state.guardrail_summary

        if not summary:
            return (
                "No guardrail results available. Run a simulation first.",
                None,
                None,
                [],
                [],
            )

        total = summary.get("total_tests", 0)
        blocked = summary.get("blocked", 0)
        allowed = summary.get("allowed", 0)
        block_rate = summary.get("overall_block_rate", 0)
        recommendation = summary.get("recommendation", "N/A")

        status_color = "green" if recommendation == "PASS" else "orange" if recommendation == "REVIEW" else "red"

        summary_text = f"""## Guardrails Summary

**Total Tests:** {total}
**Blocked:** {blocked} ({block_rate:.1f}%)
**Allowed:** {allowed}

**Recommendation:** <span style="color: {status_color}; font-weight: bold">{recommendation}</span>
"""

        # Block rate pie chart
        block_fig = px.pie(
            values=[blocked, allowed],
            names=["Blocked", "Allowed"],
            title="Block Rate",
            color_discrete_sequence=["#28a745", "#dc3545"],
        )

        # Category block rates
        cat_stats = summary.get("category_stats", {})
        if cat_stats:
            categories = list(cat_stats.keys())
            block_rates = [cat_stats[c].get("block_rate", 0) for c in categories]

            cat_fig = px.bar(
                x=categories,
                y=block_rates,
                title="Block Rate by Category",
                labels={"x": "Category", "y": "Block Rate (%)"},
                color=block_rates,
                color_continuous_scale=["red", "yellow", "green"],
            )
        else:
            cat_fig = None

        # Categories table
        cats_data = []
        for cat, stats in sorted(cat_stats.items(), key=lambda x: x[1].get("block_rate", 0)):
            cat_total = stats.get("total", 0)
            cat_blocked = stats.get("blocked", 0)
            cat_rate = stats.get("block_rate", 0)
            status = "OK" if cat_rate >= 95 else "WARN" if cat_rate >= 80 else "CRITICAL"
            cats_data.append([cat, cat_total, cat_blocked, f"{cat_rate:.1f}%", status])

        # Models table
        model_stats = summary.get("model_stats", {})
        models_data = []
        for model, stats in sorted(model_stats.items(), key=lambda x: x[1].get("block_rate", 0)):
            m_total = stats.get("total", 0)
            m_blocked = stats.get("blocked", 0)
            m_rate = stats.get("block_rate", 0)
            models_data.append([model, m_total, m_blocked, f"{m_rate:.1f}%"])

        return summary_text, block_fig, cat_fig, cats_data, models_data

    gr.Markdown("## Simulation Results")

    with gr.Tabs():
        with gr.TabItem("Operations"):
            refresh_ops_btn = gr.Button("Refresh Results", variant="secondary")

            ops_summary = gr.Markdown(
                value="Click 'Refresh Results' to load data",
            )

            with gr.Row():
                ops_success_chart = gr.Plot(label="Success Rate")
                ops_types_chart = gr.Plot(label="Agent Type Distribution")

            with gr.Row():
                ops_types_table = gr.Dataframe(
                    headers=["Agent Type", "Calls", "Percentage"],
                    label="Agent Type Distribution",
                )

                ops_models_table = gr.Dataframe(
                    headers=["Model", "Calls", "Percentage"],
                    label="Model Distribution",
                )

        with gr.TabItem("Guardrails"):
            refresh_guard_btn = gr.Button("Refresh Results", variant="secondary")

            guard_summary = gr.Markdown(
                value="Click 'Refresh Results' to load data",
            )

            with gr.Row():
                guard_block_chart = gr.Plot(label="Block Rate")
                guard_cats_chart = gr.Plot(label="Category Block Rates")

            with gr.Row():
                guard_cats_table = gr.Dataframe(
                    headers=["Category", "Total", "Blocked", "Block Rate", "Status"],
                    label="Category Statistics",
                )

                guard_models_table = gr.Dataframe(
                    headers=["Model", "Total", "Blocked", "Block Rate"],
                    label="Model Statistics",
                )

    # Event handlers
    refresh_ops_btn.click(
        fn=load_operations_results,
        outputs=[ops_summary, ops_success_chart, ops_types_chart, ops_types_table, ops_models_table],
    )

    refresh_guard_btn.click(
        fn=load_guardrails_results,
        outputs=[guard_summary, guard_block_chart, guard_cats_chart, guard_cats_table, guard_models_table],
    )
