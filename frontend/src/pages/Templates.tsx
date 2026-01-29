import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getTemplates, getTemplate } from '@/lib/api'
import { cn } from '@/lib/utils'
import {
  FileText,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Bot,
  Building2,
  Cpu,
  Users
} from 'lucide-react'
import type { TemplateDetail } from '@/types'

export default function Templates() {
  const [expandedTemplate, setExpandedTemplate] = useState<string | null>(null)

  const { data: templatesData, isLoading, refetch } = useQuery({
    queryKey: ['templates'],
    queryFn: getTemplates,
  })

  const toggleExpand = (templateId: string) => {
    setExpandedTemplate(expandedTemplate === templateId ? null : templateId)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Industry Templates</h2>
          <p className="text-muted-foreground">
            Pre-configured profiles for creating AI agents
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent"
        >
          <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Templates Grid */}
      <div className="space-y-4">
        {templatesData?.templates.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground rounded-lg border border-border">
            <FileText className="h-12 w-12 mb-4" />
            <p>No templates found</p>
            <p className="text-sm">Add industry templates to the templates directory</p>
          </div>
        ) : (
          templatesData?.templates.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              isExpanded={expandedTemplate === template.id}
              onToggle={() => toggleExpand(template.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}

function TemplateCard({
  template,
  isExpanded,
  onToggle,
}: {
  template: { id: string; name: string; description?: string; version: string; agent_types_count: number; departments_count: number }
  isExpanded: boolean
  onToggle: () => void
}) {
  const { data: details, isLoading } = useQuery({
    queryKey: ['template', template.id],
    queryFn: () => getTemplate(template.id),
    enabled: isExpanded,
  })

  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-6 hover:bg-accent/50 transition-colors text-left"
      >
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
            <FileText className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h3 className="text-lg font-semibold">{template.name}</h3>
            {template.description && (
              <p className="text-sm text-muted-foreground mt-1">
                {template.description}
              </p>
            )}
            <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Bot className="h-4 w-4" />
                {template.agent_types_count} agent types
              </span>
              <span className="flex items-center gap-1">
                <Building2 className="h-4 w-4" />
                {template.departments_count} departments
              </span>
              <span className="text-xs bg-muted px-2 py-0.5 rounded">
                v{template.version}
              </span>
            </div>
          </div>
        </div>
        {isExpanded ? (
          <ChevronUp className="h-5 w-5 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-5 w-5 text-muted-foreground" />
        )}
      </button>

      {isExpanded && (
        <div className="border-t border-border p-6 bg-muted/30">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : details ? (
            <TemplateDetails details={details} />
          ) : (
            <p className="text-muted-foreground">Failed to load template details</p>
          )}
        </div>
      )}
    </div>
  )
}

function TemplateDetails({ details }: { details: TemplateDetail }) {
  return (
    <div className="space-y-6">
      {/* Agent Types */}
      <div>
        <h4 className="font-semibold mb-3 flex items-center gap-2">
          <Bot className="h-4 w-4" />
          Agent Types
        </h4>
        <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
          {details.agent_types.map((agentType) => (
            <div
              key={agentType.id}
              className="rounded-lg border border-border bg-card p-3"
            >
              <p className="font-medium text-sm">{agentType.name}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {agentType.department}
              </p>
              {agentType.description && (
                <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                  {agentType.description}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Departments */}
      <div>
        <h4 className="font-semibold mb-3 flex items-center gap-2">
          <Users className="h-4 w-4" />
          Departments
        </h4>
        <div className="flex flex-wrap gap-2">
          {details.departments.map((dept) => (
            <span
              key={dept.code}
              className="inline-flex items-center gap-1 rounded-lg border border-border bg-card px-3 py-1.5 text-sm"
            >
              <span className="font-medium">{dept.name}</span>
              <span className="text-muted-foreground">({dept.code})</span>
            </span>
          ))}
        </div>
      </div>

      {/* Models */}
      <div>
        <h4 className="font-semibold mb-3 flex items-center gap-2">
          <Cpu className="h-4 w-4" />
          Model Configuration
        </h4>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-2">
              Preferred Models
            </p>
            <div className="flex flex-wrap gap-2">
              {details.preferred_models.length > 0 ? (
                details.preferred_models.map((model) => (
                  <span
                    key={model}
                    className="rounded bg-primary/10 text-primary px-2 py-1 text-xs font-medium"
                  >
                    {model}
                  </span>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">Any available model</span>
              )}
            </div>
          </div>
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-2">
              Allowed Models
            </p>
            <div className="flex flex-wrap gap-2">
              {details.allowed_models.length > 0 ? (
                details.allowed_models.map((model) => (
                  <span
                    key={model}
                    className="rounded bg-muted px-2 py-1 text-xs"
                  >
                    {model}
                  </span>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">All models allowed</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Organization Prefix */}
      <div>
        <h4 className="font-semibold mb-2 flex items-center gap-2">
          <Building2 className="h-4 w-4" />
          Organization Prefix
        </h4>
        <p className="text-sm">
          <code className="rounded bg-muted px-2 py-1">{details.organization_prefix}</code>
        </p>
      </div>
    </div>
  )
}
