import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import {
  getTemplates,
  getDaemonStatus,
  getDaemonHistory,
  startDaemon,
  stopDaemon,
  startSimulation,
  stopSimulation,
  getSimulationStatus,
  getSimulationResults,
} from '@/lib/api'
import { cn } from '@/lib/utils'
import {
  PlayCircle,
  Square,
  Activity,
  AlertCircle,
  CheckCircle,
  TrendingUp,
  Clock,
  Zap,
} from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

export default function Simulation() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'daemon' | 'onetime'>('daemon')
  const [selectedProfile, setSelectedProfile] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Daemon config
  const [intervalSeconds, setIntervalSeconds] = useState(60)
  const [callsMin, setCallsMin] = useState(5)
  const [callsMax, setCallsMax] = useState(15)
  const [threads, setThreads] = useState(3)
  const [operationsWeight, setOperationsWeight] = useState(80)

  // One-time simulation config
  const [numCalls, setNumCalls] = useState(100)
  const [simThreads, setSimThreads] = useState(5)
  const [delay, setDelay] = useState(0.5)
  const [simType, setSimType] = useState('operations')

  // Chart style: 'dot' | 'line' | 'curve'
  const [chartStyle, setChartStyle] = useState<'dot' | 'line' | 'curve'>('dot')

  const { data: templatesData } = useQuery({ queryKey: ['templates'], queryFn: getTemplates })
  const { data: daemonStatus } = useQuery({
    queryKey: ['daemon-status'],
    queryFn: getDaemonStatus,
    refetchInterval: 3000,
    placeholderData: keepPreviousData,
  })
  const { data: historyData } = useQuery({
    queryKey: ['daemon-history'],
    queryFn: () => getDaemonHistory(60),
    refetchInterval: 5000,
    enabled: daemonStatus?.is_running,
    placeholderData: keepPreviousData,
  })
  const { data: simStatus } = useQuery({
    queryKey: ['simulation-status'],
    queryFn: getSimulationStatus,
    refetchInterval: 2000,
  })
  const { data: simResults, refetch: refetchResults } = useQuery({
    queryKey: ['simulation-results'],
    queryFn: getSimulationResults,
    enabled: !simStatus?.is_running,
  })

  const startDaemonMutation = useMutation({
    mutationFn: startDaemon,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['daemon-status'] })
      queryClient.invalidateQueries({ queryKey: ['status'] })
      setSuccess('Daemon started')
      setError('')
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to start daemon')
      setSuccess('')
    },
  })

  const stopDaemonMutation = useMutation({
    mutationFn: stopDaemon,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['daemon-status'] })
      queryClient.invalidateQueries({ queryKey: ['status'] })
      setSuccess('Daemon stopped')
      setError('')
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to stop daemon')
      setSuccess('')
    },
  })

  const startSimMutation = useMutation({
    mutationFn: startSimulation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['simulation-status'] })
      queryClient.invalidateQueries({ queryKey: ['simulation-results'] })
      setSuccess('Simulation started')
      setError('')
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to start simulation')
      setSuccess('')
    },
  })

  const stopSimMutation = useMutation({
    mutationFn: stopSimulation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['simulation-status'] })
      setTimeout(() => refetchResults(), 1000)
      setSuccess('Simulation stopped')
      setError('')
    },
  })

  const handleStartDaemon = () => {
    if (!selectedProfile) {
      setError('Please select a profile')
      return
    }
    startDaemonMutation.mutate({
      profile_id: selectedProfile,
      interval_seconds: intervalSeconds,
      calls_per_batch_min: callsMin,
      calls_per_batch_max: callsMax,
      threads: threads,
      operations_weight: operationsWeight,
    })
  }

  const handleStartSimulation = () => {
    if (!selectedProfile) {
      setError('Please select a profile')
      return
    }
    startSimMutation.mutate({
      profile_id: selectedProfile,
      num_calls: numCalls,
      threads: simThreads,
      delay: delay,
      simulation_type: simType,
    })
  }

  const metrics = daemonStatus?.metrics

  // Transform history data to show calls per interval (delta) instead of cumulative
  // Memoized to prevent unnecessary recalculations and chart flickering
  const chartData = useMemo(() => {
    if (!historyData?.history) return []
    return historyData.history
      .map((point, index, arr) => {
        if (index === 0) {
          return {
            timestamp: point.timestamp,
            calls_per_interval: 0,
            operations_per_interval: 0,
            guardrails_per_interval: 0,
          }
        }
        const prev = arr[index - 1]
        return {
          timestamp: point.timestamp,
          calls_per_interval: Math.max(0, point.total_calls - prev.total_calls),
          operations_per_interval: Math.max(0, point.total_operations - prev.total_operations),
          guardrails_per_interval: Math.max(0, point.total_guardrails - prev.total_guardrails),
        }
      })
      .slice(1) // Remove first point (which has 0 delta)
  }, [historyData?.history])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Simulation</h2>
        <p className="text-muted-foreground">Run simulations and manage the daemon</p>
      </div>

      {/* Alerts */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 rounded-lg border border-green-500 bg-green-500/10 p-4 text-green-500">
          <CheckCircle className="h-4 w-4" />
          {success}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-border">
        <button
          onClick={() => setActiveTab('daemon')}
          className={cn(
            'px-4 py-2 text-sm font-medium border-b-2 -mb-px',
            activeTab === 'daemon'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          Daemon
        </button>
        <button
          onClick={() => setActiveTab('onetime')}
          className={cn(
            'px-4 py-2 text-sm font-medium border-b-2 -mb-px',
            activeTab === 'onetime'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          One-Time Simulation
        </button>
      </div>

      {activeTab === 'daemon' ? (
        <div className="space-y-6">
          {/* Daemon Status */}
          <div className="rounded-lg border border-border bg-card p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div
                  className={cn(
                    'h-3 w-3 rounded-full',
                    daemonStatus?.is_running ? 'bg-green-500 animate-pulse' : 'bg-zinc-500'
                  )}
                />
                <h3 className="text-lg font-semibold">
                  {daemonStatus?.is_running ? 'Daemon Running' : 'Daemon Stopped'}
                </h3>
              </div>
              {daemonStatus?.is_running ? (
                <button
                  onClick={() => stopDaemonMutation.mutate()}
                  disabled={stopDaemonMutation.isPending}
                  className="inline-flex items-center gap-2 rounded-lg bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground hover:bg-destructive/90"
                >
                  <Square className="h-4 w-4" />
                  Stop Daemon
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <select
                    value={selectedProfile}
                    onChange={(e) => setSelectedProfile(e.target.value)}
                    className="rounded-lg border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="">Select profile...</option>
                    {templatesData?.templates.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={handleStartDaemon}
                    disabled={startDaemonMutation.isPending || !selectedProfile}
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                  >
                    <PlayCircle className="h-4 w-4" />
                    Start Daemon
                  </button>
                </div>
              )}
            </div>

            {/* Daemon Config (when stopped) */}
            {!daemonStatus?.is_running && (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-4 pt-4 border-t border-border">
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">Interval (s)</label>
                  <input
                    type="number"
                    value={intervalSeconds}
                    onChange={(e) => setIntervalSeconds(parseInt(e.target.value) || 60)}
                    className="w-full rounded border border-input bg-background px-2 py-1 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">Min Calls</label>
                  <input
                    type="number"
                    value={callsMin}
                    onChange={(e) => setCallsMin(parseInt(e.target.value) || 5)}
                    className="w-full rounded border border-input bg-background px-2 py-1 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">Max Calls</label>
                  <input
                    type="number"
                    value={callsMax}
                    onChange={(e) => setCallsMax(parseInt(e.target.value) || 15)}
                    className="w-full rounded border border-input bg-background px-2 py-1 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">Threads</label>
                  <input
                    type="number"
                    value={threads}
                    onChange={(e) => setThreads(parseInt(e.target.value) || 3)}
                    className="w-full rounded border border-input bg-background px-2 py-1 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">Ops Weight %</label>
                  <input
                    type="number"
                    value={operationsWeight}
                    onChange={(e) => setOperationsWeight(parseInt(e.target.value) || 80)}
                    className="w-full rounded border border-input bg-background px-2 py-1 text-sm"
                  />
                </div>
              </div>
            )}

            {/* Daemon Metrics */}
            {daemonStatus?.is_running && metrics && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                <MetricCard icon={Zap} label="Total Calls" value={metrics.total_calls} />
                <MetricCard icon={TrendingUp} label="Success Rate" value={`${metrics.success_rate.toFixed(1)}%`} />
                <MetricCard icon={Clock} label="Avg Latency" value={`${metrics.avg_latency_ms.toFixed(0)}ms`} />
                <MetricCard icon={Activity} label="Runtime" value={metrics.runtime} />
              </div>
            )}
          </div>

          {/* Daemon Chart */}
          {daemonStatus?.is_running && (
            <div className="rounded-lg border border-border bg-card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Calls per Interval</h3>
                <select
                  value={chartStyle}
                  onChange={(e) => setChartStyle(e.target.value as 'dot' | 'line' | 'curve')}
                  className="rounded-lg border border-input bg-background px-3 py-1.5 text-sm"
                >
                  <option value="dot">Dot Style</option>
                  <option value="line">Line Style</option>
                  <option value="curve">Curve Style</option>
                </select>
              </div>
              <div className="h-64">
                {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis
                      dataKey="timestamp"
                      tick={{ fontSize: 11 }}
                      tickFormatter={(v) => new Date(v).toLocaleTimeString()}
                    />
                    <YAxis
                      tick={{ fontSize: 12 }}
                      domain={[0, 'auto']}
                      allowDecimals={false}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                      }}
                      labelFormatter={(v) => new Date(v).toLocaleTimeString()}
                      formatter={(value: number, name: string) => {
                        const labels: Record<string, string> = {
                          calls_per_interval: 'Total Calls',
                          operations_per_interval: 'Operations',
                          guardrails_per_interval: 'Guardrails',
                        }
                        return [value, labels[name] || name]
                      }}
                    />
                    <Line
                      type={chartStyle === 'curve' ? 'monotone' : 'linear'}
                      dataKey="calls_per_interval"
                      name="calls_per_interval"
                      stroke={chartStyle === 'dot' ? 'transparent' : 'hsl(var(--primary))'}
                      strokeWidth={chartStyle === 'dot' ? 0 : 2}
                      dot={chartStyle === 'dot' ? { fill: 'hsl(var(--primary))', r: 4 } : false}
                      isAnimationActive={false}
                    />
                    <Line
                      type={chartStyle === 'curve' ? 'monotone' : 'linear'}
                      dataKey="operations_per_interval"
                      name="operations_per_interval"
                      stroke={chartStyle === 'dot' ? 'transparent' : 'hsl(142, 76%, 36%)'}
                      strokeWidth={chartStyle === 'dot' ? 0 : 2}
                      dot={chartStyle === 'dot' ? { fill: 'hsl(142, 76%, 36%)', r: 4 } : false}
                      isAnimationActive={false}
                    />
                    <Line
                      type={chartStyle === 'curve' ? 'monotone' : 'linear'}
                      dataKey="guardrails_per_interval"
                      name="guardrails_per_interval"
                      stroke={chartStyle === 'dot' ? 'transparent' : 'hsl(38, 92%, 50%)'}
                      strokeWidth={chartStyle === 'dot' ? 0 : 2}
                      dot={chartStyle === 'dot' ? { fill: 'hsl(38, 92%, 50%)', r: 4 } : false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-muted-foreground">
                    Collecting data...
                  </div>
                )}
              </div>
              <div className="flex items-center justify-center gap-6 mt-3 text-xs">
                <div className="flex items-center gap-2">
                  <div className={chartStyle === 'dot' ? 'w-3 h-3 rounded-full bg-primary' : 'w-4 h-0.5 bg-primary'} />
                  <span className="text-muted-foreground">Total Calls</span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className={chartStyle === 'dot' ? 'w-3 h-3 rounded-full' : 'w-4 h-0.5'}
                    style={{ backgroundColor: 'hsl(142, 76%, 36%)' }}
                  />
                  <span className="text-muted-foreground">Operations</span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className={chartStyle === 'dot' ? 'w-3 h-3 rounded-full' : 'w-4 h-0.5'}
                    style={{ backgroundColor: 'hsl(38, 92%, 50%)' }}
                  />
                  <span className="text-muted-foreground">Guardrails</span>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          {/* One-Time Simulation */}
          <div className="rounded-lg border border-border bg-card p-6">
            <h3 className="text-lg font-semibold mb-4">Run One-Time Simulation</h3>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Profile</label>
                <select
                  value={selectedProfile}
                  onChange={(e) => setSelectedProfile(e.target.value)}
                  className="w-full rounded border border-input bg-background px-2 py-1 text-sm"
                >
                  <option value="">Select...</option>
                  {templatesData?.templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Num Calls</label>
                <input
                  type="number"
                  value={numCalls}
                  onChange={(e) => setNumCalls(parseInt(e.target.value) || 100)}
                  className="w-full rounded border border-input bg-background px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Threads</label>
                <input
                  type="number"
                  value={simThreads}
                  onChange={(e) => setSimThreads(parseInt(e.target.value) || 5)}
                  className="w-full rounded border border-input bg-background px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Delay (s)</label>
                <input
                  type="number"
                  step="0.1"
                  value={delay}
                  onChange={(e) => setDelay(parseFloat(e.target.value) || 0.5)}
                  className="w-full rounded border border-input bg-background px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Type</label>
                <select
                  value={simType}
                  onChange={(e) => setSimType(e.target.value)}
                  className="w-full rounded border border-input bg-background px-2 py-1 text-sm"
                >
                  <option value="operations">Operations</option>
                  <option value="guardrails">Guardrails</option>
                  <option value="both">Both</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-4 mt-4">
              {simStatus?.is_running ? (
                <button
                  onClick={() => stopSimMutation.mutate()}
                  className="inline-flex items-center gap-2 rounded-lg bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground"
                >
                  <Square className="h-4 w-4" />
                  Stop
                </button>
              ) : (
                <button
                  onClick={handleStartSimulation}
                  disabled={startSimMutation.isPending || !selectedProfile}
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
                >
                  <PlayCircle className="h-4 w-4" />
                  Start
                </button>
              )}

              {simStatus?.is_running && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Activity className="h-4 w-4 animate-pulse" />
                  {simStatus.progress} / {simStatus.total} - {simStatus.current_message}
                </div>
              )}
            </div>
          </div>

          {/* Simulation Results */}
          {!simStatus?.is_running && simResults?.success && simResults.metrics && (
            <div className="rounded-lg border border-border bg-card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Simulation Results</h3>
                {simResults.completed_at && (
                  <span className="text-sm text-muted-foreground">
                    Completed: {new Date(simResults.completed_at).toLocaleString()}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                <MetricCard
                  icon={Zap}
                  label="Total Calls"
                  value={simResults.metrics.total_calls}
                />
                <MetricCard
                  icon={CheckCircle}
                  label="Successful"
                  value={simResults.metrics.successful_calls}
                />
                <MetricCard
                  icon={AlertCircle}
                  label="Failed"
                  value={simResults.metrics.failed_calls}
                />
                <MetricCard
                  icon={TrendingUp}
                  label="Success Rate"
                  value={`${simResults.metrics.success_rate.toFixed(1)}%`}
                />
                <MetricCard
                  icon={Clock}
                  label="Avg Latency"
                  value={`${simResults.metrics.avg_latency_ms.toFixed(0)}ms`}
                />
                <MetricCard
                  icon={Activity}
                  label="Max Latency"
                  value={`${simResults.metrics.max_latency_ms.toFixed(0)}ms`}
                />
              </div>
            </div>
          )}

          {/* No Results Message */}
          {!simStatus?.is_running && (!simResults?.success || !simResults?.metrics?.total_calls) && (
            <div className="rounded-lg border border-border bg-card p-6">
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <Activity className="h-12 w-12 mb-4" />
                <p className="text-center">No simulation results yet</p>
                <p className="text-sm text-center mt-1">Run a simulation to see results here</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function MetricCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType
  label: string
  value: string | number
}) {
  return (
    <div className="rounded-lg bg-muted p-4">
      <div className="flex items-center gap-2 text-muted-foreground mb-1">
        <Icon className="h-4 w-4" />
        <span className="text-xs">{label}</span>
      </div>
      <p className="text-xl font-semibold">{value}</p>
    </div>
  )
}
