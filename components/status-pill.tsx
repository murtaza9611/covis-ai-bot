'use client'

import { cn } from '@/lib/utils'

export type ChatApiHealth = 'idle' | 'ok' | 'error'

type StatusPillProps = {
  health: ChatApiHealth
  className?: string
}

export function StatusPill({ health, className }: StatusPillProps) {
  const config = {
    idle: {
      dot: 'bg-zinc-400',
      label: 'Ready to chat',
      sub: 'Covis assistant',
      ring: 'ring-zinc-200/80 dark:ring-zinc-500/25',
    },
    ok: {
      dot: 'bg-emerald-500 shadow-[0_0_0_2px_rgba(16,185,129,0.2)]',
      label: 'Assistant online',
      sub: 'Covis connected',
      ring: 'ring-emerald-500/20',
    },
    error: {
      dot: 'bg-amber-500',
      label: 'Connection issue',
      sub: 'Try sending again',
      ring: 'ring-amber-500/25',
    },
  }[health]

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'flex min-w-0 max-w-[min(100%,18rem)] items-center gap-x-1.5 rounded-lg border border-border/70 bg-muted/45 px-2 py-1.5 shadow-sm backdrop-blur-sm sm:max-w-none sm:gap-x-2 sm:rounded-xl sm:px-3 sm:py-2 dark:bg-muted/25',
        'motion-safe:transition-all motion-safe:duration-200 motion-safe:hover:border-primary/25 motion-safe:hover:shadow-md',
        config.ring,
        'ring-1',
        className,
      )}
    >
      <span
        className={cn(
          'h-1.5 w-1.5 shrink-0 rounded-full',
          config.dot,
          health === 'idle' && 'motion-safe:animate-pulse',
        )}
        aria-hidden
      />
      <span className="min-w-0 truncate text-[10px] font-semibold text-foreground sm:text-xs">
        {config.label}
      </span>
      <span className="hidden shrink-0 text-muted-foreground/70 sm:inline" aria-hidden>
        ·
      </span>
      <span className="hidden min-w-0 truncate text-[10px] text-muted-foreground sm:inline sm:text-xs">
        {config.sub}
      </span>
    </div>
  )
}
