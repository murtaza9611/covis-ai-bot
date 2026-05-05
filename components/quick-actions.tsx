'use client'

import { Bug, CheckSquare, BarChart3 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface QuickActionsProps {
  onSelect: (action: string) => void
  disabled?: boolean
}

export function QuickActions({ onSelect, disabled }: QuickActionsProps) {
  const actions = [
    { id: 'bug', label: 'Report Bug', icon: Bug, color: 'bg-red-500/20 hover:bg-red-500/30 text-red-400' },
    { id: 'task', label: 'Create Task', icon: CheckSquare, color: 'bg-green-500/20 hover:bg-green-500/30 text-green-400' },
    { id: 'status', label: 'Check Status', icon: BarChart3, color: 'bg-blue-500/20 hover:bg-blue-500/30 text-blue-400' },
  ]

  return (
    <div className="flex flex-wrap gap-2 justify-center mb-6">
      {actions.map(({ id, label, icon: Icon, color }) => (
        <Button
          key={id}
          onClick={() => onSelect(label)}
          disabled={disabled}
          className={`${color} rounded-full h-10 px-6 flex items-center gap-2 transition-all duration-200`}
          variant="outline"
        >
          <Icon className="w-4 h-4" />
          <span className="text-sm font-medium">{label}</span>
        </Button>
      ))}
    </div>
  )
}
