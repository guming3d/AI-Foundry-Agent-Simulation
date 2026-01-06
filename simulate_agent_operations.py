import os
import csv
import random
import time
from datetime import datetime
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
import threading
from queue import Queue
import json

load_dotenv()

# Query templates for each agent type
QUERY_TEMPLATES = {
    "CustomerSupport": [
        "How do I track my order #ORDER-{}?",
        "I need to return a product I purchased last week. What's the process?",
        "My account is locked. Can you help me reset it?",
        "What are your customer service hours?",
        "I didn't receive a confirmation email for my order. Can you resend it?",
        "How can I update my shipping address?",
        "What's your refund policy?",
        "I have a question about warranty coverage on product #{}",
        "Can you help me with a billing issue?",
        "How do I cancel my subscription?"
    ],
    "CatalogEnrichment": [
        "Generate product descriptions for new inventory items in category {}",
        "Tag and categorize the following product: [Product Name]",
        "Extract features from product images batch #{}",
        "Enrich product metadata for SKU range {}-{}",
        "Generate SEO-friendly product titles for category {}",
        "Classify products into appropriate taxonomy categories",
        "Extract and normalize product attributes from supplier data",
        "Generate product comparison tables for category {}",
        "Identify missing product information in catalog section {}",
        "Create product bundles based on purchase patterns"
    ],
    "PricingOptimization": [
        "Analyze pricing trends for product category {} over the last 30 days",
        "Recommend optimal price point for new product launch in segment {}",
        "Calculate price elasticity for top {} products",
        "Generate dynamic pricing strategy for promotional period",
        "Compare our prices with competitors for category {}",
        "Forecast revenue impact of {}% price increase on product line",
        "Identify products with suboptimal pricing in region {}",
        "Analyze margin optimization opportunities for SKU {}",
        "Generate markdown schedule for end-of-season inventory",
        "Calculate break-even pricing for new product with {}% margin target"
    ],
    "StoreOps": [
        "Check inventory levels for store #{} in real-time",
        "Report on foot traffic patterns for store #{} today",
        "Identify restocking needs for high-traffic stores",
        "Analyze temperature anomalies in refrigeration units at store #{}",
        "Generate staff scheduling recommendations for store #{} next week",
        "Monitor energy consumption patterns across {} stores",
        "Alert on unusual activity detected at store #{}",
        "Optimize store layout based on customer flow data",
        "Track equipment maintenance schedules for region {}",
        "Analyze checkout queue times for store #{}"
    ],
    "SupplyChain": [
        "Track shipment status for order #{} in transit",
        "Optimize delivery routes for region {} this week",
        "Forecast inventory needs for next {} days based on demand",
        "Analyze supplier performance metrics for vendor #{}",
        "Identify supply chain bottlenecks in distribution center {}",
        "Calculate optimal reorder points for product category {}",
        "Monitor customs clearance status for international shipments",
        "Predict potential delays in supply chain for upcoming holiday",
        "Optimize warehouse space utilization in facility #{}",
        "Analyze transportation costs for route optimization"
    ],
    "FraudDetection": [
        "Analyze transaction pattern for account #{} - potential fraud alert",
        "Review suspicious payment activity from IP address {}",
        "Flag multiple failed login attempts on account #{}",
        "Investigate chargeback claim for order #{}",
        "Detect anomalous purchase pattern: {} high-value items in {} minutes",
        "Verify identity for account showing unusual location changes",
        "Analyze card-not-present transaction risk for order #{}",
        "Review account takeover indicators for user #{}",
        "Monitor for potential return fraud on order #{}",
        "Investigate velocity abuse pattern on payment method #{}"
    ],
    "MarketingCopy": [
        "Generate email campaign copy for {} product launch",
        "Create social media posts for spring sale promotion",
        "Write product landing page content for new {} collection",
        "Generate A/B test variants for campaign headline",
        "Create customer testimonial showcase copy",
        "Write seasonal promotion announcement for {} holiday",
        "Generate SMS marketing message for flash sale (under 160 chars)",
        "Create blog post about product category {} trends",
        "Write abandoned cart recovery email sequence",
        "Generate push notification copy for app users about {} promotion"
    ],
    "HRAssistant": [
        "What are the paid time off policies for employees?",
        "Help me understand the benefits enrollment process",
        "What's the procedure for requesting parental leave?",
        "Explain the performance review cycle and timeline",
        "How do I access my pay stubs and tax documents?",
        "What training programs are available for {} role?",
        "Explain the company's remote work policy",
        "How do I submit an expense report?",
        "What are the career development opportunities in {} department?",
        "Help me with the onboarding checklist for new hires"
    ],
    "FinanceAnalyst": [
        "Generate quarterly revenue report for {} department",
        "Analyze budget variance for cost center #{} this month",
        "Forecast cash flow for next {} months",
        "Calculate ROI for marketing campaign investment of ${}",
        "Generate P&L statement for business unit {}",
        "Analyze operating expenses trend over past {} quarters",
        "Calculate break-even analysis for new product line",
        "Review accounts receivable aging report",
        "Generate financial ratios dashboard for executive review",
        "Analyze capital expenditure requests for {} project"
    ]
}

# Initialize project client
project_client = AIProjectClient(
    endpoint=os.environ.get("PROJECT_ENDPOINT", 'https://foundry-control-plane.services.ai.azure.com/api/projects/foundry-control-plane'),
    credential=DefaultAzureCredential(),
)

openai_client = project_client.get_openai_client()

class AgentSimulator:
    def __init__(self, agents_csv_path):
        self.agents = self.load_agents(agents_csv_path)
        self.metrics = []
        self.lock = threading.Lock()

    def load_agents(self, csv_path):
        """Load agent information from CSV."""
        agents = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                agents.append(row)
        print(f"Loaded {len(agents)} agents from {csv_path}")
        return agents

    def extract_agent_type(self, agent_name):
        """Extract agent type from agent name (e.g., 'ORG01-CustomerSupport-AG001' -> 'CustomerSupport')."""
        parts = agent_name.split('-')
        if len(parts) >= 2:
            return parts[1]
        return "Unknown"

    def generate_query(self, agent_type):
        """Generate a contextually appropriate query for the agent type."""
        if agent_type not in QUERY_TEMPLATES:
            return "Can you help me with my request?"

        template = random.choice(QUERY_TEMPLATES[agent_type])

        # Fill in template placeholders with random data
        if '{}' in template:
            placeholders = template.count('{}')
            random_values = []
            for _ in range(placeholders):
                random_values.append(str(random.randint(1000, 9999)))
            query = template.format(*random_values)
        else:
            query = template

        return query

    def call_agent(self, agent_info, query):
        """Call a specific agent with a query and track metrics."""
        agent_name = agent_info['name']
        start_time = time.time()
        success = False
        error_message = None
        response_text = None
        response_length = 0

        try:
            # Create conversation
            conversation = openai_client.conversations.create()

            # Send query to agent
            response = openai_client.responses.create(
                conversation=conversation.id,
                extra_body={"agent": {"name": agent_name, "type": "agent_reference"}},
                input=query,
            )

            response_text = response.output_text
            response_length = len(response_text) if response_text else 0
            success = True

        except Exception as e:
            error_message = str(e)
            print(f"✗ Error calling agent {agent_name}: {error_message}")

        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        # Record metrics
        metric = {
            'timestamp': datetime.now().isoformat(),
            'agent_id': agent_info['agent_id'],
            'agent_name': agent_name,
            'azure_id': agent_info['azure_id'],
            'model': agent_info['model'],
            'org_id': agent_info['org_id'],
            'agent_type': self.extract_agent_type(agent_name),
            'query': query,
            'query_length': len(query),
            'response_text': response_text[:200] if response_text else None,  # Truncate for CSV
            'response_length': response_length,
            'latency_ms': round(latency_ms, 2),
            'success': success,
            'error_message': error_message
        }

        with self.lock:
            self.metrics.append(metric)

        status = "✓" if success else "✗"
        print(f"{status} [{agent_name}] Query: '{query[:60]}...' | Latency: {latency_ms:.0f}ms")

        return metric

    def simulate_single_call(self):
        """Simulate a single agent call with random agent and query."""
        agent = random.choice(self.agents)
        agent_type = self.extract_agent_type(agent['name'])
        query = self.generate_query(agent_type)

        return self.call_agent(agent, query)

    def run_simulation(self, num_calls=100, parallel_threads=5, delay_between_calls=0.5):
        """Run simulation with multiple parallel calls."""
        print("\n" + "=" * 80)
        print(f"Starting Agent Operation Simulation")
        print("=" * 80)
        print(f"Total calls to simulate: {num_calls}")
        print(f"Parallel threads: {parallel_threads}")
        print(f"Delay between calls: {delay_between_calls}s")
        print("=" * 80 + "\n")

        call_queue = Queue()
        for i in range(num_calls):
            call_queue.put(i)

        def worker():
            while not call_queue.empty():
                try:
                    call_queue.get_nowait()
                    self.simulate_single_call()
                    time.sleep(delay_between_calls)
                except:
                    break

        threads = []
        for _ in range(parallel_threads):
            t = threading.Thread(target=worker)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        print("\n" + "=" * 80)
        print("Simulation Complete")
        print("=" * 80)

    def save_metrics(self, output_path='simulation_metrics.csv'):
        """Save collected metrics to CSV."""
        if not self.metrics:
            print("No metrics to save.")
            return

        fieldnames = [
            'timestamp', 'agent_id', 'agent_name', 'azure_id', 'model', 'org_id',
            'agent_type', 'query', 'query_length', 'response_text', 'response_length',
            'latency_ms', 'success', 'error_message'
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.metrics)

        print(f"\n✓ Metrics saved to {output_path}")

    def generate_summary_report(self):
        """Generate summary statistics from metrics."""
        if not self.metrics:
            print("No metrics to analyze.")
            return

        total_calls = len(self.metrics)
        successful_calls = sum(1 for m in self.metrics if m['success'])
        failed_calls = total_calls - successful_calls

        latencies = [m['latency_ms'] for m in self.metrics if m['success']]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0

        # Agent type distribution
        agent_type_counts = {}
        for m in self.metrics:
            agent_type = m['agent_type']
            agent_type_counts[agent_type] = agent_type_counts.get(agent_type, 0) + 1

        # Model distribution
        model_counts = {}
        for m in self.metrics:
            model = m['model']
            model_counts[model] = model_counts.get(model, 0) + 1

        print("\n" + "=" * 80)
        print("Simulation Summary Report")
        print("=" * 80)
        print(f"Total API Calls: {total_calls}")
        print(f"Successful: {successful_calls} ({successful_calls/total_calls*100:.1f}%)")
        print(f"Failed: {failed_calls} ({failed_calls/total_calls*100:.1f}%)")
        print(f"\nLatency Statistics:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  Min: {min_latency:.2f}ms")
        print(f"  Max: {max_latency:.2f}ms")
        print(f"\nAgent Type Distribution:")
        for agent_type, count in sorted(agent_type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {agent_type}: {count} calls ({count/total_calls*100:.1f}%)")
        print(f"\nModel Distribution:")
        for model, count in sorted(model_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {model}: {count} calls ({count/total_calls*100:.1f}%)")
        print("=" * 80)

        # Save summary to JSON
        summary = {
            'total_calls': total_calls,
            'successful_calls': successful_calls,
            'failed_calls': failed_calls,
            'success_rate': round(successful_calls/total_calls*100, 2),
            'avg_latency_ms': round(avg_latency, 2),
            'min_latency_ms': round(min_latency, 2),
            'max_latency_ms': round(max_latency, 2),
            'agent_type_distribution': agent_type_counts,
            'model_distribution': model_counts
        }

        with open('simulation_summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        print(f"\n✓ Summary report saved to simulation_summary.json")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Simulate AI Foundry Agent Operations')
    parser.add_argument('--agents-csv', default='created_agents_results.csv',
                        help='Path to agents CSV file')
    parser.add_argument('--num-calls', type=int, default=100,
                        help='Number of agent calls to simulate')
    parser.add_argument('--threads', type=int, default=5,
                        help='Number of parallel threads')
    parser.add_argument('--delay', type=float, default=0.5,
                        help='Delay between calls in seconds')
    parser.add_argument('--output', default='simulation_metrics.csv',
                        help='Output CSV file for metrics')

    args = parser.parse_args()

    # Run simulation
    simulator = AgentSimulator(args.agents_csv)
    simulator.run_simulation(
        num_calls=args.num_calls,
        parallel_threads=args.threads,
        delay_between_calls=args.delay
    )

    # Save results
    simulator.save_metrics(args.output)
    simulator.generate_summary_report()
