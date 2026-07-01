'use client'

import { Sparkles } from 'lucide-react'

const suggestions = [
  'Report a bug',
  'Check project status',
  "What's due this week?",
]

type ChatEmptyStateProps = {
  onPick?: (text: string) => void
}

export function ChatEmptyState({ onPick }: ChatEmptyStateProps) {
  return (
    <div className="flex items-center justify-center py-10 text-center sm:py-14 md:py-20">
      <div className="mx-auto flex w-full max-w-xl flex-col items-center gap-6 rounded-2xl  border-border/70 bg-card/90 px-5 py-8 shadow-sm ring-0 ring-black/[0.03] backdrop-blur-sm dark:ring-white/[0.06] sm:px-7">
        <div className="space-y-2">
          <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/[0.12] text-primary shadow-sm ring-1 ring-primary/20 motion-safe:animate-in motion-safe:fade-in motion-safe:zoom-in-95 motion-safe:duration-500 motion-safe:[animation-delay:120ms] motion-safe:animate-[pulse_2.4s_ease-in-out_infinite] dark:bg-primary/[0.2] dark:ring-primary/30">
            <Sparkles className="h-5 w-5 motion-safe:animate-[bounce_2.4s_ease-in-out_infinite] motion-safe:drop-shadow-[0_0_10px_rgba(139,92,246,0.45)] dark:motion-safe:drop-shadow-[0_0_12px_rgba(167,139,250,0.55)]" aria-hidden />
          </div>
          <p className="text-xl font-semibold tracking-tight text-foreground">Start a conversation</p>
          <p className="mx-auto max-w-md text-sm leading-relaxed text-muted-foreground">
            Choose a quick prompt or type below — your messages sync with Covis so bugs and tasks stay in one place.
          </p>
        </div>
        <div className="flex w-full flex-wrap items-center justify-center gap-2.5">
          {suggestions.map((label) => (
            <button
              key={label}
              type="button"
              className="rounded-full border border-primary/20 bg-primary/[0.08] px-5 py-2.5 text-sm font-medium text-foreground shadow-sm ring-1 ring-primary/10 motion-safe:transition-all motion-safe:duration-200 motion-safe:hover:-translate-y-0.5 hover:border-primary/35 hover:bg-primary/[0.14] hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:border-primary/30 dark:bg-primary/[0.16] dark:ring-primary/20 dark:hover:bg-primary/[0.24]"
              onClick={() => onPick?.(label)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
