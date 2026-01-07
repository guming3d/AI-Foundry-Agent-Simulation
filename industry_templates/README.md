# Industry Templates

Each `*.yaml` file defines an industry profile that drives agent generation and the generated simulation code.

Edit these templates to match your customer story:
- Add/remove `agent_archetypes`
- Update `purpose`, `tools`, and `query_templates`
- Change `default_org_id` if you want a different naming prefix

Template schema (minimal):
```yaml
id: retail
name: Retail & eCommerce
default_org_id: ORG01
agent_archetypes:
  - agent_type: CustomerSupport
    display_name: Customer Support
    owner: Customer Service
    purpose: Help customers with orders, returns, billing, and account issues.
    tools: CRM, OrderLookup, ReturnsPolicy
    query_templates:
      - "How do I track my order #ORDER-{}?"
      - "I need to return a product I purchased last week. What's the process?"
```

