import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getStatus, getModels, getAgents, getTemplates, getDaemonStatus } from '@/lib/api'
import {
  Bot,
  GitBranch,
  FileText,
  Cpu,
  ArrowRight,
  Activity,
} from 'lucide-react'

export default function Dashboard() {
  const { data: status } = useQuery({ queryKey: ['status'], queryFn: getStatus })
  const { data: modelsData } = useQuery({ queryKey: ['models'], queryFn: () => getModels() })
  const { data: agentsData } = useQuery({ queryKey: ['agents'], queryFn: getAgents })
  const { data: templatesData } = useQuery({ queryKey: ['templates'], queryFn: getTemplates })
  const { data: daemonStatus } = useQuery({
    queryKey: ['daemon-status'],
    queryFn: getDaemonStatus,
    refetchInterval: 5000,
  })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Overview of your Microsoft Foundry Bootstrap environment
        </p>
      </div>

      {/* Status Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatusCard
          title="Models"
          value={modelsData?.count ?? 0}
          description="Available model deployments"
          icon={Cpu}
          href="/settings"
        />
        <StatusCard
          title="Agents"
          value={agentsData?.count ?? 0}
          description="Created agents"
          icon={Bot}
          href="/agents"
        />
        <StatusCard
          title="Workflows"
          value={status?.workflows_count ?? 0}
          description="Created workflows"
          icon={GitBranch}
          href="/workflows"
        />
        <StatusCard
          title="Templates"
          value={templatesData?.count ?? 0}
          description="Industry templates"
          icon={FileText}
          href="/templates"
        />
      </div>

      {/* Daemon Status */}
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">Daemon Status</h3>
            <p className="text-sm text-muted-foreground">
              Continuous simulation daemon for production traffic
            </p>
          </div>
          <Link
            to="/simulation"
            className="flex items-center gap-2 text-sm text-primary hover:underline"
          >
            Manage <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        {daemonStatus?.is_running ? (
          <div className="mt-4 grid gap-4 md:grid-cols-4">
            <MetricCard
              label="Total Calls"
              value={daemonStatus.metrics?.total_calls ?? 0}
            />
            <MetricCard
              label="Success Rate"
              value={`${daemonStatus.metrics?.success_rate?.toFixed(1) ?? 0}%`}
            />
            <MetricCard
              label="Avg Latency"
              value={`${daemonStatus.metrics?.avg_latency_ms?.toFixed(0) ?? 0}ms`}
            />
            <MetricCard
              label="Runtime"
              value={daemonStatus.metrics?.runtime ?? '0s'}
            />
          </div>
        ) : (
          <div className="mt-4 flex items-center gap-2 text-muted-foreground">
            <Activity className="h-4 w-4" />
            <span>Daemon is not running</span>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="rounded-lg border border-border bg-card p-6">
        <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
        <div className="grid gap-4 md:grid-cols-3">
          <QuickAction
            title="Create Agents"
            description="Create agents from industry templates"
            href="/agents"
          />
          <QuickAction
            title="Run Simulation"
            description="Execute one-time simulation tests"
            href="/simulation"
          />
          <QuickAction
            title="Run Evaluations"
            description="Evaluate agents with test datasets"
            href="/evaluations"
          />
        </div>
      </div>
    </div>
  )
}

function StatusCard({
  title,
  value,
  description,
  icon: Icon,
  href,
}: {
  title: string
  value: number | string
  description: string
  icon: React.ElementType
  href: string
}) {
  return (
    <Link
      to={href}
      className="rounded-lg border border-border bg-card p-6 hover:bg-accent transition-colors"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-xs text-muted-foreground mt-1">{description}</p>
        </div>
        <Icon className="h-8 w-8 text-muted-foreground" />
      </div>
    </Link>
  )
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-muted p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
    </div>
  )
}

function QuickAction({
  title,
  description,
  href,
}: {
  title: string
  description: string
  href: string
}) {
  return (
    <Link
      to={href}
      className="flex items-center justify-between rounded-lg border border-border p-4 hover:bg-accent transition-colors"
    >
      <div>
        <p className="font-medium">{title}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <ArrowRight className="h-5 w-5 text-muted-foreground" />
    </Link>
  )
}
