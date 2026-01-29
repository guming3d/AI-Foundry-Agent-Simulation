import { useQuery } from '@tanstack/react-query'
import { getStatus } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Circle, RefreshCw } from 'lucide-react'

export default function Header() {
  const { data: status, isLoading, refetch } = useQuery({
    queryKey: ['status'],
    queryFn: getStatus,
    refetchInterval: 5000,
  })

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-card px-6">
      <div className="flex items-center gap-3">
        <img src="/foundry-logo.svg" alt="Foundry Logo" className="h-8 w-8" />
        <h1 className="text-lg font-semibold">Microsoft Foundry Bootstrap</h1>
      </div>
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-4 text-sm">
          <StatusBadge label="Models" count={status?.models_count ?? 0} />
          <StatusBadge label="Agents" count={status?.agents_count ?? 0} />
          <StatusBadge label="Workflows" count={status?.workflows_count ?? 0} />
          <div className="flex items-center gap-1.5">
            <Circle
              className={cn(
                'h-2 w-2',
                status?.daemon_running ? 'fill-green-500 text-green-500' : 'fill-zinc-500 text-zinc-500'
              )}
            />
            <span className="text-muted-foreground">
              Daemon: {status?.daemon_running ? 'Running' : 'Stopped'}
            </span>
          </div>
        </div>
        <button
          onClick={() => refetch()}
          className="p-2 text-muted-foreground hover:text-foreground transition-colors"
          disabled={isLoading}
        >
          <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
        </button>
      </div>
    </header>
  )
}

function StatusBadge({ label, count }: { label: string; count: number }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-muted-foreground">{label}:</span>
      <span className="font-medium">{count}</span>
    </div>
  )
}
