import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  FileText,
  Bot,
  GitBranch,
  PlayCircle,
  ClipboardCheck,
  Settings,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Templates', href: '/templates', icon: FileText },
  { name: 'Agents', href: '/agents', icon: Bot },
  { name: 'Workflows', href: '/workflows', icon: GitBranch },
  { name: 'Simulation', href: '/simulation', icon: PlayCircle },
  { name: 'Evaluations', href: '/evaluations', icon: ClipboardCheck },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Sidebar() {
  const location = useLocation()

  return (
    <div className="flex w-64 flex-col bg-card border-r border-border">
      <div className="flex h-16 items-center gap-2 px-6 border-b border-border">
        <img src="/foundry-logo.svg" alt="Foundry Logo" className="h-8 w-8" />
        <div className="flex flex-col">
          <span className="font-semibold text-sm">Foundry Bootstrap</span>
          <span className="text-xs text-muted-foreground">Control Plane</span>
        </div>
      </div>
      <nav className="flex-1 space-y-1 p-4">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href
          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </Link>
          )
        })}
      </nav>
      <div className="border-t border-border p-4">
        <div className="text-xs text-muted-foreground">
          Microsoft Foundry Bootstrap v1.0.0
        </div>
      </div>
    </div>
  )
}
