'use client'

import { Bot } from 'lucide-react'

export function ChatTypingIndicator() {
  return (
    <div
      className="motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 mb-5 flex items-end gap-3 duration-300"
      role="status"
      aria-live="polite"
      aria-label="Assistant is typing"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary/25 to-primary/5 text-primary shadow-sm ring-2 ring-primary/10">
        <Bot className="h-5 w-5" aria-hidden strokeWidth={2} />
      </div>
      <div className="min-w-0 max-w-[min(90%,24rem)]">
        <p className="mb-1.5 pl-0.5 text-xs font-medium text-muted-foreground">Assistant</p>
        <div className="inline-flex items-center gap-1.5 rounded-2xl rounded-tl-md border border-zinc-200/90 bg-white px-4 py-3 shadow-sm">
          <span
            className="h-2 w-2 rounded-full bg-primary/70 motion-safe:animate-bounce"
            style={{ animationDelay: '0ms' }}
          />
          <span
            className="h-2 w-2 rounded-full bg-primary/70 motion-safe:animate-bounce"
            style={{ animationDelay: '150ms' }}
          />
          <span
            className="h-2 w-2 rounded-full bg-primary/70 motion-safe:animate-bounce"
            style={{ animationDelay: '300ms' }}
          />
        </div>
      </div>
    </div>
  )
}
