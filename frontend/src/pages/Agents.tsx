import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAgents, getTemplates, getModels, createAgents, deleteAllAgents, deleteAgent, getAgentProgress, getAgentDeletionProgress } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Bot, Plus, Trash2, RefreshCw, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'

export default function Agents() {
  const queryClient = useQueryClient()
  const [isCreating, setIsCreating] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [selectedModels, setSelectedModels] = useState<string[]>([])
  const [agentCount, setAgentCount] = useState(1)
  const [orgCount, setOrgCount] = useState(1)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const { data: agentsData, isLoading: agentsLoading, refetch: refetchAgents } = useQuery({
    queryKey: ['agents'],
    queryFn: getAgents,
  })
  const { data: templatesData } = useQuery({ queryKey: ['templates'], queryFn: getTemplates })
  const { data: modelsData } = useQuery({ queryKey: ['models'], queryFn: () => getModels() })
  const { data: progressData } = useQuery({
    queryKey: ['agent-progress'],
    queryFn: getAgentProgress,
    refetchInterval: isProcessing ? 1000 : false,
    enabled: isProcessing,
  })
  const { data: deletionProgressData } = useQuery({
    queryKey: ['agent-deletion-progress'],
    queryFn: getAgentDeletionProgress,
    refetchInterval: isDeleting ? 1000 : false,
    enabled: isDeleting,
  })

  const createMutation = useMutation({
    mutationFn: createAgents,
    onMutate: () => {
      setIsProcessing(true)
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      queryClient.invalidateQueries({ queryKey: ['status'] })
      setIsProcessing(false)
      setIsCreating(false)
      setSuccess(`Created ${data.created_count} agents successfully`)
      setError('')
    },
    onError: (err: any) => {
      setIsProcessing(false)
      setError(err.response?.data?.detail || 'Failed to create agents')
      setSuccess('')
    },
  })

  const deleteAllMutation = useMutation({
    mutationFn: deleteAllAgents,
    onMutate: () => {
      setIsDeleting(true)
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      queryClient.invalidateQueries({ queryKey: ['status'] })
      setIsDeleting(false)
      setSuccess(data.message || 'All agents deleted')
      setError('')
    },
    onError: (err: any) => {
      setIsDeleting(false)
      setError(err.response?.data?.detail || 'Failed to delete agents')
      setSuccess('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      queryClient.invalidateQueries({ queryKey: ['status'] })
    },
  })

  const handleCreate = () => {
    if (!selectedTemplate || selectedModels.length === 0) {
      setError('Please select a template and at least one model')
      return
    }
    createMutation.mutate({
      profile_id: selectedTemplate,
      agent_count: agentCount,
      org_count: orgCount,
      models: selectedModels,
    })
  }

  const handleModelToggle = (modelName: string) => {
    setSelectedModels((prev) =>
      prev.includes(modelName)
        ? prev.filter((m) => m !== modelName)
        : [...prev, modelName]
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Agents</h2>
          <p className="text-muted-foreground">Manage AI agents in your project</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetchAgents()}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent"
          >
            <RefreshCw className={cn('h-4 w-4', agentsLoading && 'animate-spin')} />
            Refresh
          </button>
          <button
            onClick={() => setIsCreating(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            Create Agents
          </button>
        </div>
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

      {/* Create Modal */}
      {isCreating && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-lg rounded-lg bg-card p-6 shadow-lg">
            <h3 className="text-lg font-semibold mb-4">Create Agents</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Industry Template</label>
                <select
                  value={selectedTemplate}
                  onChange={(e) => setSelectedTemplate(e.target.value)}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="">Select a template...</option>
                  {templatesData?.templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Models</label>
                <div className="max-h-40 overflow-y-auto space-y-2 rounded-lg border border-input p-3">
                  {modelsData?.models.map((m) => (
                    <label key={m.name} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedModels.includes(m.name)}
                        onChange={() => handleModelToggle(m.name)}
                        className="rounded border-input"
                      />
                      <span className="text-sm">{m.name}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Agents per Type</label>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={agentCount}
                    onChange={(e) => setAgentCount(parseInt(e.target.value) || 1)}
                    className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Organizations</label>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={orgCount}
                    onChange={(e) => setOrgCount(parseInt(e.target.value) || 1)}
                    className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
              </div>
            </div>

            {/* Progress Indicator */}
            {createMutation.isPending && progressData && (
              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">
                    {progressData.message || 'Creating agents...'}
                  </span>
                  <span className="font-medium">
                    {progressData.current} / {progressData.total}
                  </span>
                </div>
                <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-primary h-full transition-all duration-300 ease-out"
                    style={{
                      width: `${progressData.total > 0 ? (progressData.current / progressData.total) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setIsCreating(false)}
                disabled={createMutation.isPending}
                className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={createMutation.isPending}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {createMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                {createMutation.isPending ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Deletion Progress Modal */}
      {isDeleting && deletionProgressData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-lg bg-card p-6 shadow-lg">
            <h3 className="text-lg font-semibold mb-4">Deleting Agents</h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  {deletionProgressData.message || 'Deleting agents...'}
                </span>
                <span className="font-medium">
                  {deletionProgressData.current} / {deletionProgressData.total}
                </span>
              </div>
              <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                <div
                  className="bg-destructive h-full transition-all duration-300 ease-out"
                  style={{
                    width: `${deletionProgressData.total > 0 ? (deletionProgressData.current / deletionProgressData.total) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Agents Table */}
      <div className="rounded-lg border border-border">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="text-sm font-medium">
            {agentsData?.count ?? 0} agents
          </span>
          {(agentsData?.count ?? 0) > 0 && (
            <button
              onClick={() => {
                if (confirm('Delete all agents? This cannot be undone.')) {
                  deleteAllMutation.mutate()
                }
              }}
              disabled={deleteAllMutation.isPending}
              className="inline-flex items-center gap-2 text-sm text-destructive hover:underline disabled:opacity-50"
            >
              {deleteAllMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
              Delete All
            </button>
          )}
        </div>
        <div className="divide-y divide-border">
          {agentsData?.agents.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Bot className="h-12 w-12 mb-4" />
              <p>No agents found</p>
              <p className="text-sm">Create agents using an industry template</p>
            </div>
          ) : (
            agentsData?.agents.map((agent) => (
              <div key={agent.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="font-medium">{agent.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {agent.model ?? 'Unknown model'} • v{agent.version ?? 0}
                  </p>
                </div>
                <button
                  onClick={() => {
                    if (confirm(`Delete agent ${agent.name}?`)) {
                      deleteMutation.mutate(agent.name)
                    }
                  }}
                  className="p-2 text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
