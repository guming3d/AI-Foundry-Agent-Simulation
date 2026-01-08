import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json

def load_and_analyze_metrics(csv_path='simulation_metrics.csv'):
    """Load metrics CSV and generate visualizations."""

    # Load data
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Create figure with subplots
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle('Agent Operation Metrics Analysis', fontsize=16, fontweight='bold')

    # 1. Success Rate
    success_counts = df['success'].value_counts()
    # Create dynamic labels and colors based on what's in the data
    labels = []
    colors = []
    for status in success_counts.index:
        if status:
            labels.append('Success')
            colors.append('#2ecc71')
        else:
            labels.append('Failed')
            colors.append('#e74c3c')

    axes[0, 0].pie(success_counts, labels=labels, autopct='%1.1f%%',
                   colors=colors, startangle=90)
    axes[0, 0].set_title('Success Rate')

    # 2. Latency Distribution
    successful_df = df[df['success'] == True]
    if len(successful_df) > 0:
        axes[0, 1].hist(successful_df['latency_ms'], bins=30, color='#3498db', edgecolor='black')
        axes[0, 1].set_xlabel('Latency (ms)')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].set_title('Latency Distribution')
        axes[0, 1].axvline(successful_df['latency_ms'].mean(), color='red',
                           linestyle='--', label=f"Mean: {successful_df['latency_ms'].mean():.2f}ms")
        axes[0, 1].legend()
    else:
        axes[0, 1].text(0.5, 0.5, 'No successful calls', ha='center', va='center', transform=axes[0, 1].transAxes)
        axes[0, 1].set_title('Latency Distribution')

    # 3. Agent Type Distribution
    agent_type_counts = df['agent_type'].value_counts()
    axes[0, 2].barh(agent_type_counts.index, agent_type_counts.values, color='#9b59b6')
    axes[0, 2].set_xlabel('Number of Calls')
    axes[0, 2].set_title('Calls by Agent Type')
    axes[0, 2].tick_params(axis='y', labelsize=8)

    # 4. Model Distribution
    model_counts = df['model'].value_counts()
    axes[1, 0].bar(range(len(model_counts)), model_counts.values, color='#f39c12')
    axes[1, 0].set_xticks(range(len(model_counts)))
    axes[1, 0].set_xticklabels(model_counts.index, rotation=45, ha='right', fontsize=8)
    axes[1, 0].set_ylabel('Number of Calls')
    axes[1, 0].set_title('Calls by Model')

    # 5. Latency by Model (box plot)
    model_latency = []
    model_labels = []
    for model in df['model'].unique():
        model_data = df[(df['model'] == model) & (df['success'] == True)]
        if len(model_data) > 0:
            model_latency.append(model_data['latency_ms'].values)
            model_labels.append(model)

    if len(model_latency) > 0:
        axes[1, 1].boxplot(model_latency, labels=model_labels)
        axes[1, 1].set_ylabel('Latency (ms)')
        axes[1, 1].set_title('Latency by Model')
        axes[1, 1].tick_params(axis='x', rotation=45, labelsize=8)
    else:
        axes[1, 1].text(0.5, 0.5, 'No successful calls', ha='center', va='center', transform=axes[1, 1].transAxes)
        axes[1, 1].set_title('Latency by Model')

    # 6. Calls Over Time
    df_sorted = df.sort_values('timestamp')
    df_sorted['call_number'] = range(1, len(df_sorted) + 1)

    # Plot successful and failed calls
    successful = df_sorted[df_sorted['success'] == True]
    failed = df_sorted[df_sorted['success'] == False]

    axes[1, 2].scatter(successful['call_number'], successful['latency_ms'],
                      alpha=0.6, s=20, color='#2ecc71', label='Success')
    if len(failed) > 0:
        axes[1, 2].scatter(failed['call_number'], [0]*len(failed),
                          alpha=0.6, s=20, color='#e74c3c', label='Failed', marker='x')
    axes[1, 2].set_xlabel('Call Number')
    axes[1, 2].set_ylabel('Latency (ms)')
    axes[1, 2].set_title('Latency Over Time')
    axes[1, 2].legend()

    plt.tight_layout()
    plt.savefig('metrics_visualization.png', dpi=300, bbox_inches='tight')
    print("✓ Visualization saved to metrics_visualization.png")

    # Generate detailed statistics
    print("\n" + "=" * 80)
    print("Detailed Statistics")
    print("=" * 80)

    print(f"\nOverall Metrics:")
    print(f"  Total Calls: {len(df)}")
    print(f"  Success Rate: {(df['success'].sum() / len(df) * 100):.2f}%")
    if len(successful_df) > 0:
        print(f"  Average Latency: {successful_df['latency_ms'].mean():.2f}ms")
        print(f"  Median Latency: {successful_df['latency_ms'].median():.2f}ms")
        print(f"  95th Percentile: {successful_df['latency_ms'].quantile(0.95):.2f}ms")
        print(f"  99th Percentile: {successful_df['latency_ms'].quantile(0.99):.2f}ms")
    else:
        print(f"  No successful calls - latency metrics unavailable")

    print(f"\nLatency by Agent Type:")
    for agent_type in df['agent_type'].unique():
        type_data = df[(df['agent_type'] == agent_type) & (df['success'] == True)]
        if len(type_data) > 0:
            print(f"  {agent_type:25s}: {type_data['latency_ms'].mean():7.2f}ms (n={len(type_data)})")

    print(f"\nLatency by Model:")
    for model in df['model'].unique():
        model_data = df[(df['model'] == model) & (df['success'] == True)]
        if len(model_data) > 0:
            print(f"  {model:30s}: {model_data['latency_ms'].mean():7.2f}ms (n={len(model_data)})")

    print(f"\nResponse Length Statistics:")
    if len(successful_df) > 0:
        print(f"  Average Response: {successful_df['response_length'].mean():.0f} characters")
        print(f"  Min Response: {successful_df['response_length'].min():.0f} characters")
        print(f"  Max Response: {successful_df['response_length'].max():.0f} characters")
    else:
        print(f"  No successful calls - response length metrics unavailable")

    print("=" * 80)

    return df

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Visualize Agent Operation Metrics')
    parser.add_argument('--input', default='simulation_metrics.csv',
                        help='Input metrics CSV file')

    args = parser.parse_args()

    df = load_and_analyze_metrics(args.input)
