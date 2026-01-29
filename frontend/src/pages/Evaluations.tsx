import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getEvaluationTemplates,
  getRecentEvaluations,
  getAgents,
  getModels,
  runEvaluations,
  getEvaluationProgress,
} from '@/lib/api'
import {
  ClipboardCheck,
  PlayCircle,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  ExternalLink,
  Activity,
} from 'lucide-react'

export default function Evaluations() {
  const queryClient = useQueryClient()
  const [isRunning, setIsRunning] = useState(false)
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([])
  const [selectedAgents, setSelectedAgents] = useState<string[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const { data: evalTemplates } = useQuery({
    queryKey: ['eval-templates'],
    queryFn: getEvaluationTemplates,
  })
  const { data: recentRuns, refetch } = useQuery({
    queryKey: ['recent-evaluations'],
    queryFn: getRecentEvaluations,
  })
  const { data: agentsData } = useQuery({ queryKey: ['agents'], queryFn: getAgents })
  const { data: modelsData } = useQuery({ queryKey: ['models'], queryFn: () => getModels() })
  const { data: progressData } = useQuery({
    queryKey: ['eval-progress'],
    queryFn: getEvaluationProgress,
    refetchInterval: isRunning ? 2000 : false,
  })

  const runMutation = useMutation({
    mutationFn: runEvaluations,
    onMutate: () => {
      setIsRunning(true)
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['recent-evaluations'] })
      setIsRunning(false)
      setSuccess(`Completed ${data.results?.length ?? 0} evaluation runs`)
      setError('')
    },
    onError: (err: any) => {
      setIsRunning(false)
      setError(err.response?.data?.detail || 'Failed to run evaluations')
      setSuccess('')
    },
  })

  const handleRun = () => {
    if (selectedTemplates.length === 0 || selectedAgents.length === 0) {
      setError('Please select at least one template and one agent')
      return
    }
    runMutation.mutate({
      template_ids: selectedTemplates,
      agent_names: selectedAgents,
      model_deployment_name: selectedModel || undefined,
    })
  }

  const handleTemplateToggle = (id: string) => {
    setSelectedTemplates((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]
    )
  }

  const handleAgentToggle = (name: string) => {
    setSelectedAgents((prev) =>
      prev.includes(name) ? prev.filter((a) => a !== name) : [...prev, name]
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Evaluations</h2>
          <p className="text-muted-foreground">Run and review agent evaluations</p>
        </div>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
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

      {/* Run Evaluations */}
      <div className="rounded-lg border border-border bg-card p-6">
        <h3 className="text-lg font-semibold mb-4">Run Evaluations</h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Templates */}
          <div>
            <label className="block text-sm font-medium mb-2">Evaluation Templates</label>
            <div className="max-h-48 overflow-y-auto space-y-2 rounded-lg border border-input p-3">
              {evalTemplates?.templates.map((t) => (
                <label key={t.id} className="flex items-start gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedTemplates.includes(t.id)}
                    onChange={() => handleTemplateToggle(t.id)}
                    className="rounded border-input mt-0.5"
                  />
                  <div>
                    <span className="text-sm font-medium">{t.display_name}</span>
                    <p className="text-xs text-muted-foreground">
                      {t.evaluators.join(', ')}
                    </p>
                  </div>
                </label>
              ))}
              {(!evalTemplates?.templates || evalTemplates.templates.length === 0) && (
                <p className="text-sm text-muted-foreground">No evaluation templates found</p>
              )}
            </div>
          </div>

          {/* Agents */}
          <div>
            <label className="block text-sm font-medium mb-2">Target Agents</label>
            <div className="max-h-48 overflow-y-auto space-y-2 rounded-lg border border-input p-3">
              {agentsData?.agents.map((a) => (
                <label key={a.name} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedAgents.includes(a.name)}
                    onChange={() => handleAgentToggle(a.name)}
                    className="rounded border-input"
                  />
                  <span className="text-sm">{a.name}</span>
                </label>
              ))}
              {(!agentsData?.agents || agentsData.agents.length === 0) && (
                <p className="text-sm text-muted-foreground">No agents found</p>
              )}
            </div>
          </div>

          {/* Model Deployment */}
          <div>
            <label className="block text-sm font-medium mb-2">Model Deployment (for model-based evals)</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">None (use agent's model)</option>
              {modelsData?.models.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-4 mt-6">
          <button
            onClick={handleRun}
            disabled={runMutation.isPending || isRunning}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            <PlayCircle className="h-4 w-4" />
            {runMutation.isPending || isRunning ? 'Running...' : 'Run Evaluations'}
          </button>

          {isRunning && progressData?.running && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Activity className="h-4 w-4 animate-pulse" />
              {progressData.progress} / {progressData.total} - {progressData.message}
            </div>
          )}
        </div>
      </div>

      {/* Recent Runs */}
      <div className="rounded-lg border border-border">
        <div className="border-b border-border px-4 py-3">
          <span className="text-sm font-medium">Recent Evaluation Runs</span>
        </div>
        <div className="divide-y divide-border">
          {(!recentRuns?.runs || recentRuns.runs.length === 0) ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <ClipboardCheck className="h-12 w-12 mb-4" />
              <p>No evaluation runs found</p>
            </div>
          ) : (
            recentRuns.runs.slice(0, 20).map((run, idx) => (
              <div key={`${run.run_id}-${idx}`} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="font-medium">{run.evaluation_name}</p>
                  <p className="text-sm text-muted-foreground">
                    Agent: {run.agent_name} • Status: {run.run_status}
                  </p>
                </div>
                {run.report_url && (
                  <a
                    href={run.report_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-sm text-primary hover:underline"
                  >
                    View Report <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
