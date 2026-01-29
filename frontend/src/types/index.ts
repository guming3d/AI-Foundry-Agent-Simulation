// API Types

export interface StatusResponse {
  status: string
  models_count: number
  agents_count: number
  workflows_count: number
  daemon_running: boolean
  templates_count: number
}

export interface Model {
  name: string
  deployment_name: string
  status: string
  capabilities: string[]
  version?: string
  model_name?: string
  model_publisher?: string
}

export interface Agent {
  name: string
  id: string
  version?: number
  model?: string
}

export interface Workflow {
  name: string
  id: string
  version?: number
}

export interface Template {
  id: string
  name: string
  description?: string
  version: string
  agent_types_count: number
  departments_count: number
}

export interface TemplateDetail {
  id: string
  name: string
  description?: string
  version: string
  organization_prefix: string
  agent_types: AgentType[]
  departments: { name: string; code: string }[]
  preferred_models: string[]
  allowed_models: string[]
}

export interface AgentType {
  id: string
  name: string
  department: string
  description?: string
}

export interface CreateAgentsRequest {
  profile_id: string
  agent_count: number
  org_count: number
  models: string[]
}

export interface CreateAgentsResponse {
  success: boolean
  created: CreatedAgentInfo[]
  failed: FailedAgentInfo[]
  total_attempted: number
  created_count: number
  failed_count: number
}

export interface CreatedAgentInfo {
  agent_id: string
  name: string
  azure_id: string
  version: number
  model: string
  org_id: string
}

export interface FailedAgentInfo {
  agent_id: string
  name: string
  org_id: string
  agent_type: string
  error: string
}

export interface DaemonMetrics {
  total_calls: number
  scheduled_calls: number
  started_calls: number
  dropped_calls: number
  inflight_calls: number
  queue_depth: number
  target_calls_per_minute: number
  successful_calls: number
  failed_calls: number
  success_rate: number
  total_operations: number
  total_guardrails: number
  blocked_guardrails: number
  avg_latency_ms: number
  p50_latency_ms: number
  p95_latency_ms: number
  max_latency_ms: number
  calls_per_minute: number
  started_calls_per_minute: number
  batches_completed: number
  runtime: string
  current_load_profile: string
  recent_errors: string[]
}

export interface DaemonStatus {
  is_running: boolean
  started_at?: string
  stopped_at?: string
  profile_id?: string
  profile_name?: string
  metrics?: DaemonMetrics
}

export interface SimulationStatus {
  is_running: boolean
  progress: number
  total: number
  current_message: string
}

export interface EvaluationTemplate {
  id: string
  display_name: string
  description?: string
  evaluators: string[]
  dataset_items_count: number
}

export interface EvaluationRun {
  evaluation_id: string
  evaluation_name: string
  eval_id: string
  agent_name: string
  run_id: string
  run_status: string
  report_url?: string
  created_at?: number
}
