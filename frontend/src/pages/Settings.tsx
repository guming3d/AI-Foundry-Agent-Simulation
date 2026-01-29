import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getModels, getHealth } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Sun, Moon, Cpu, CheckCircle, XCircle, RefreshCw } from 'lucide-react'

export default function Settings() {
  const [isDark, setIsDark] = useState(false)

  const { data: modelsData, isLoading: modelsLoading, refetch: refetchModels } = useQuery({
    queryKey: ['models'],
    queryFn: () => getModels(true),
  })

  const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 10000,
  })

  useEffect(() => {
    // Initialize from document class
    setIsDark(document.documentElement.classList.contains('dark'))
  }, [])

  const toggleTheme = () => {
    const newIsDark = !isDark
    setIsDark(newIsDark)
    if (newIsDark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Settings</h2>
        <p className="text-muted-foreground">Configure your application</p>
      </div>

      {/* Theme */}
      <div className="rounded-lg border border-border bg-card p-6">
        <h3 className="text-lg font-semibold mb-4">Appearance</h3>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">Theme</p>
            <p className="text-sm text-muted-foreground">
              Toggle between light and dark mode
            </p>
          </div>
          <button
            onClick={toggleTheme}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent"
          >
            {isDark ? (
              <>
                <Sun className="h-4 w-4" />
                Light Mode
              </>
            ) : (
              <>
                <Moon className="h-4 w-4" />
                Dark Mode
              </>
            )}
          </button>
        </div>
      </div>

      {/* Connection Status */}
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Connection Status</h3>
          <button
            onClick={() => refetchHealth()}
            className="p-2 text-muted-foreground hover:text-foreground"
            disabled={healthLoading}
          >
            <RefreshCw className={cn('h-4 w-4', healthLoading && 'animate-spin')} />
          </button>
        </div>
        <div className="flex items-center gap-3">
          {health?.status === 'healthy' ? (
            <>
              <CheckCircle className="h-5 w-5 text-green-500" />
              <span className="text-green-500 font-medium">API Connected</span>
            </>
          ) : (
            <>
              <XCircle className="h-5 w-5 text-destructive" />
              <span className="text-destructive font-medium">API Disconnected</span>
            </>
          )}
        </div>
        <p className="text-sm text-muted-foreground mt-2">
          Backend server: http://localhost:8000
        </p>
      </div>

      {/* Available Models */}
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Available Models</h3>
          <button
            onClick={() => refetchModels()}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-accent"
            disabled={modelsLoading}
          >
            <RefreshCw className={cn('h-3 w-3', modelsLoading && 'animate-spin')} />
            Refresh
          </button>
        </div>

        {modelsData?.count === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
            <Cpu className="h-12 w-12 mb-4" />
            <p>No models found</p>
            <p className="text-sm">Deploy models in your Microsoft Foundry project</p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {modelsData?.models.map((model) => (
              <div key={model.name} className="py-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{model.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {model.model_publisher && model.model_name
                        ? `${model.model_publisher}/${model.model_name}`
                        : 'Azure AI Deployment'}
                    </p>
                  </div>
                  <span
                    className={cn(
                      'text-xs font-medium px-2 py-1 rounded',
                      model.status === 'available'
                        ? 'bg-green-500/10 text-green-500'
                        : 'bg-zinc-500/10 text-zinc-500'
                    )}
                  >
                    {model.status}
                  </span>
                </div>
                {model.capabilities.length > 0 && (
                  <div className="flex gap-2 mt-2">
                    {model.capabilities.map((cap) => (
                      <span
                        key={cap}
                        className="text-xs bg-muted px-2 py-0.5 rounded"
                      >
                        {cap}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* About */}
      <div className="rounded-lg border border-border bg-card p-6">
        <h3 className="text-lg font-semibold mb-4">About</h3>
        <div className="space-y-2 text-sm">
          <p>
            <span className="text-muted-foreground">Application:</span>{' '}
            Microsoft Foundry Bootstrap
          </p>
          <p>
            <span className="text-muted-foreground">Version:</span> 1.0.0
          </p>
          <p>
            <span className="text-muted-foreground">Description:</span>{' '}
            A comprehensive system for creating, testing, and demonstrating AI agents using Microsoft Foundry Control Plane features.
          </p>
        </div>
      </div>
    </div>
  )
}
