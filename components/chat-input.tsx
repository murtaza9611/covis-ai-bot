'use client'

import { Keyboard, Loader2, Send } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface ChatInputProps {
  value: string | undefined
  onChange: (value: string) => void
  onSubmit: (e: React.FormEvent) => void
  disabled?: boolean
  isSending?: boolean
}

export function ChatInput({
  value = '',
  onChange,
  onSubmit,
  disabled,
  isSending = false,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const prevSendingRef = useRef(false)
  const minHeight = 52
  const maxHeight = 160

  const hardDisabled = !!disabled
  const sendingLocked = isSending && !hardDisabled

  const resizeTextarea = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = '0px'
    const next = Math.min(el.scrollHeight, maxHeight)
    el.style.height = `${Math.max(next, minHeight)}px`
    el.style.overflowY = el.scrollHeight > maxHeight ? 'auto' : 'hidden'
  }

  useEffect(() => {
    resizeTextarea()
  }, [value])

  useEffect(() => {
    if (!isSending) return
    const id = requestAnimationFrame(() => {
      textareaRef.current?.focus({ preventScroll: true })
    })
    return () => cancelAnimationFrame(id)
  }, [isSending])

  useEffect(() => {
    if (prevSendingRef.current && !isSending) {
      textareaRef.current?.focus({ preventScroll: true })
    }
    prevSendingRef.current = isSending
  }, [isSending])

  const busy = hardDisabled || isSending

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (busy || !value?.trim()) return
        onSubmit(e)
      }}
      className="shrink-0 bg-canvas px-4 py-2 md:px-8 md:py-4 pb-[max(0.5rem,env(safe-area-inset-bottom))] md:pb-[max(1rem,env(safe-area-inset-bottom))]"
    >
      <div className="relative mx-auto w-full max-w-3xl">
        <div className="rounded-2xl border border-border bg-card p-1.5 shadow-sm ring-1 ring-black/[0.03] motion-safe:transition-[box-shadow,border-color] motion-safe:duration-200 motion-safe:focus-within:border-primary/25 motion-safe:focus-within:shadow-md motion-safe:focus-within:ring-primary/10 dark:ring-white/[0.06]">
          <label htmlFor="covis-chat-input" className="sr-only">
            Message
          </label>
          <div className="relative">
            <textarea
              ref={textareaRef}
              id="covis-chat-input"
              rows={1}
              placeholder="Describe the issue you want to report..."
              value={value}
              onChange={(e) => {
                onChange(e.target.value)
                resizeTextarea()
              }}
              onKeyDown={(e) => {
                if (e.key !== 'Enter' || e.shiftKey || busy) return
                e.preventDefault()
                if (!value?.trim()) return
                e.currentTarget.form?.requestSubmit()
              }}
              disabled={hardDisabled}
              readOnly={sendingLocked}
              aria-busy={isSending || undefined}
              className={cn(
                'min-h-[52px] w-full resize-none overflow-x-hidden [overflow-wrap:anywhere] rounded-xl py-3 pl-4 pr-[3.75rem] text-sm leading-relaxed text-foreground antialiased',
                /* Light: crisp typing well — inset depth + readable border */
                'border border-border/75 bg-background shadow-[inset_0_1px_3px_oklch(0_0_0/0.06)]',
                'placeholder:text-muted-foreground/90',
                'hover:border-border hover:shadow-[inset_0_1px_3px_oklch(0_0_0/0.05)]',
                'focus-visible:border-primary/45 focus-visible:bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/18',
                'disabled:opacity-70 read-only:cursor-wait',
                'motion-safe:transition-[background-color,border-color,box-shadow] motion-safe:duration-200',
                /* Dark: flatter, softer — unchanged intent */
                'dark:border-transparent dark:bg-muted/40 dark:shadow-none',
                'dark:placeholder:text-muted-foreground/85',
                'dark:hover:border-transparent',
                'dark:focus-visible:border-primary/30 dark:focus-visible:bg-muted/55 dark:focus-visible:ring-ring/45',
              )}
            />
            <Button
              type="submit"
              disabled={busy || !value?.trim()}
              title={isSending ? 'Sending…' : 'Send message'}
              aria-busy={isSending}
              className="group/send absolute bottom-4.5 right-2.5 h-8 w-8 min-h-8 min-w-8 rounded-full bg-primary p-0 text-primary-foreground shadow-sm motion-safe:transition-all motion-safe:duration-200 motion-safe:hover:scale-[1.02] motion-safe:hover:shadow-md motion-safe:hover:brightness-[1.03] motion-safe:active:scale-[0.98] disabled:pointer-events-none disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-ring"
            >
              {isSending ? (
                <Loader2 className="h-[18px] w-[18px] animate-spin" aria-hidden />
              ) : (
                <Send className="h-[18px] w-[18px] motion-safe:transition-transform motion-safe:duration-200 motion-safe:group-hover/send:translate-x-0.5 motion-safe:group-hover/send:-translate-y-0.5" aria-hidden />
              )}
            </Button>
          </div>
        </div>
        <div className="mt-2 hidden flex-col items-center gap-1 sm:flex sm:flex-row sm:justify-center sm:gap-3">
          <p className="flex items-center gap-1.5 text-center text-[11px] text-primary/75 dark:text-muted-foreground">
            <Keyboard
              className="hidden h-3.5 w-3.5 shrink-0 text-primary/65 dark:text-muted-foreground sm:inline"
              aria-hidden
            />
            <span>
              <kbd className="rounded-md border border-primary/20 bg-primary/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-foreground dark:border-border dark:bg-muted/70 dark:text-foreground">
                Enter
              </kbd>{' '}
              to send ·{' '}
              <kbd className="rounded-md border border-primary/20 bg-primary/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-foreground dark:border-border dark:bg-muted/70 dark:text-foreground">
                Shift
              </kbd>
              +
              <kbd className="rounded-md border border-primary/20 bg-primary/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-foreground dark:border-border dark:bg-muted/70 dark:text-foreground">
                Enter
              </kbd>{' '}
              new line
            </span>
          </p>
        </div>
      </div>
    </form>
  )
}
