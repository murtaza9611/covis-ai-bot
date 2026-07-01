'use client'

import { useEffect, useRef, type ComponentType } from 'react'
import { MessageSquare, MessagesSquare, PenLine, Sparkles } from 'lucide-react'
import type { QADriveMode, QAChatAction, QATurnRecord } from '@/lib/covis-qa-api'
import { scoreBadgeClass } from '@/lib/covis-qa-api'
import { isPrefillAction, isQuickReplyAction, type ChatAction } from '@/lib/covis-api'
import { cn } from '@/lib/utils'

type QATranscriptProps = {
  banner: string | null
  turns: QATurnRecord[]
  isProcessingTurn?: boolean
  nextTurnNumber?: number
  driveMode?: QADriveMode
  isRunning?: boolean
  onCtaSelect?: (payload: string, label: string) => void
  onCtaPrefill?: (payload: string) => void
  ctaActionsEnabled?: boolean
}

export function QATranscript({
  banner,
  turns,
  isProcessingTurn = false,
  nextTurnNumber,
  driveMode = 'AUTO',
  isRunning = false,
  onCtaSelect,
  onCtaPrefill,
  ctaActionsEnabled = false,
}: QATranscriptProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const turnNumber = nextTurnNumber ?? turns.length + 1
  const latestTurnNumber = turns.length > 0 ? turns[turns.length - 1]?.turn_number : null

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [turns.length, isProcessingTurn])

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-border/70 bg-card/95 shadow-sm ring-1 ring-black/[0.03] dark:ring-white/[0.06]">
      <div className="shrink-0 border-b border-border/60 px-3 py-2">
        <h2 className="text-sm font-semibold">Live transcript</h2>
      </div>
      <div
        ref={scrollRef}
        className="chat-thread-scroll flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain"
      >
        {turns.length === 0 && !isProcessingTurn ? (
          <div className="flex min-h-full flex-1 items-center justify-center p-3">
            <TranscriptEmptyState driveMode={driveMode} isRunning={isRunning} />
          </div>
        ) : (
          <div className="p-3">
            {banner ? (
              <pre className="mb-4 whitespace-pre-wrap rounded-lg bg-muted/60 p-3 font-mono text-xs text-muted-foreground">
                {banner}
              </pre>
            ) : null}
            <div className="space-y-6">
              {turns.map((turn) => (
                <TurnBlock
                  key={turn.turn_number}
                  turn={turn}
                  actionsEnabled={
                    ctaActionsEnabled &&
                    !isProcessingTurn &&
                    turn.turn_number === latestTurnNumber
                  }
                  onCtaSelect={onCtaSelect}
                  onCtaPrefill={onCtaPrefill}
                />
              ))}
              {isProcessingTurn ? <QATurnLoader turnNumber={turnNumber} /> : null}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function TranscriptEmptyState({
  driveMode,
  isRunning,
}: {
  driveMode: QADriveMode
  isRunning: boolean
}) {
  if (isRunning) {
    return (
      <EmptyStateCard
        icon={MessagesSquare}
        title="Waiting for first turn"
        description="The session is active. Client messages and Assist replies will stream here as each turn completes."
        badge="Live"
      />
    )
  }

  const isManual = driveMode === 'MANUAL'

  return (
    <EmptyStateCard
      icon={isManual ? PenLine : Sparkles}
      title={isManual ? 'Ready for your messages' : 'Ready to simulate a client'}
      description={
        isManual
          ? 'Start a manual session, then type client messages below. Each reply from COVIS Assist appears here with a quality score.'
          : 'Start an auto session and the QA agent will send client-style messages for you. Every Assist reply shows up here with a turn score.'
      }
      steps={[
        isManual
          ? 'You write the client message — or tap CTA chips after each Assist reply'
          : 'Agent generates short messages or taps CTAs when offered',
        'Client bubbles on the right, Assist on the left',
        'CTA chips appear under Assist replies and are scored in the report',
      ]}
    />
  )
}

function EmptyStateCard({
  icon: Icon,
  title,
  description,
  steps,
  badge,
}: {
  icon: ComponentType<{ className?: string }>
  title: string
  description: string
  steps?: string[]
  badge?: string
}) {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col items-center gap-3 rounded-xl border border-border/60 bg-muted/20 px-4 py-4 text-center shadow-sm ring-1 ring-black/[0.03] dark:ring-white/[0.06]">
        <div className="relative">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/12 text-primary ring-1 ring-primary/20">
            <Icon className="size-5" aria-hidden />
          </div>
          {badge ? (
            <span className="absolute -right-2 -top-2 rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-primary-foreground shadow-sm">
              {badge}
            </span>
          ) : null}
        </div>

        <div className="space-y-1">
          <h3 className="text-sm font-semibold tracking-tight text-foreground">{title}</h3>
          <p className="text-xs leading-relaxed text-muted-foreground">{description}</p>
        </div>

        {steps?.length ? (
          <ul className="w-full space-y-1.5 text-left">
            {steps.map((step) => (
              <li
                key={step}
                className="flex gap-2 rounded-md border border-border/50 bg-card/60 px-2.5 py-1.5 text-[11px] leading-snug text-muted-foreground"
              >
                <MessageSquare className="mt-0.5 size-3 shrink-0 text-primary/70" aria-hidden />
                {step}
              </li>
            ))}
          </ul>
        ) : null}
    </div>
  )
}

function QATurnLoader({ turnNumber }: { turnNumber: number }) {
  return (
    <div
      className="space-y-2 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 duration-300"
      role="status"
      aria-live="polite"
      aria-label={`Processing turn ${turnNumber}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-muted-foreground">
          Turn {turnNumber}
        </span>
        <span className="text-xs font-medium text-primary motion-safe:animate-pulse">
          In progress…
        </span>
      </div>

      <div className="flex justify-end">
        <div className="max-w-[90%] rounded-2xl bg-primary/15 px-4 py-3 text-primary">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide opacity-70">
            Client
          </p>
          <TypingDots label="Generating message" />
        </div>
      </div>

      <div className="flex justify-start">
        <div className="max-w-[90%] rounded-2xl border border-border/60 bg-muted/40 px-4 py-3">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide opacity-70">
            COVIS Assist
          </p>
          <TypingDots label="Waiting for reply" />
        </div>
      </div>
    </div>
  )
}

function TypingDots({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="sr-only">{label}</span>
      <span
        className="h-2 w-2 rounded-full bg-current opacity-70 motion-safe:animate-bounce"
        style={{ animationDelay: '0ms' }}
      />
      <span
        className="h-2 w-2 rounded-full bg-current opacity-70 motion-safe:animate-bounce"
        style={{ animationDelay: '150ms' }}
      />
      <span
        className="h-2 w-2 rounded-full bg-current opacity-70 motion-safe:animate-bounce"
        style={{ animationDelay: '300ms' }}
      />
    </div>
  )
}

function TurnBlock({
  turn,
  actionsEnabled = false,
  onCtaSelect,
  onCtaPrefill,
}: {
  turn: QATurnRecord
  actionsEnabled?: boolean
  onCtaSelect?: (payload: string, label: string) => void
  onCtaPrefill?: (payload: string) => void
}) {
  const score = turn.grade.weighted_score
  const actions = normalizeQaActions(turn.bot_actions)
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-muted-foreground">
          Turn {turn.turn_number}
        </span>
        <span
          className={cn(
            'rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums',
            scoreBadgeClass(score),
          )}
        >
          {score.toFixed(0)}/100
        </span>
      </div>
      <Bubble
        role="client"
        text={turn.client_message}
        viaCta={turn.client_message_source === 'cta'}
        ctaLabel={turn.client_cta_label}
      />
      <AssistBubble
        text={turn.bot_reply}
        actions={actions}
        actionsEnabled={actionsEnabled}
        onCtaSelect={onCtaSelect}
        onCtaPrefill={onCtaPrefill}
      />
    </div>
  )
}

function normalizeQaActions(actions: QAChatAction[] | undefined): ChatAction[] {
  return (actions ?? []).map((action) => ({
    id: action.id,
    label: action.label,
    type: action.type === 'prefill' ? 'prefill' : 'quick_reply',
    payload: action.payload,
  }))
}

function Bubble({
  role,
  text,
  viaCta = false,
  ctaLabel,
}: {
  role: 'client' | 'assist'
  text: string
  viaCta?: boolean
  ctaLabel?: string | null
}) {
  const isClient = role === 'client'
  return (
    <div className={cn('flex', isClient ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[90%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
          isClient
            ? 'bg-primary text-primary-foreground'
            : 'border border-border/60 bg-muted/40 text-foreground',
        )}
      >
        <div className="mb-1 flex flex-wrap items-center gap-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide opacity-70">
            {isClient ? 'Client' : 'COVIS Assist'}
          </p>
          {viaCta ? (
            <span className="rounded-full bg-primary-foreground/15 px-2 py-0.5 text-[10px] font-medium normal-case tracking-normal">
              via CTA{ctaLabel ? `: ${ctaLabel}` : ''}
            </span>
          ) : null}
        </div>
        <p className="whitespace-pre-wrap">{text}</p>
      </div>
    </div>
  )
}

function AssistBubble({
  text,
  actions,
  actionsEnabled = false,
  onCtaSelect,
  onCtaPrefill,
}: {
  text: string
  actions: ChatAction[]
  actionsEnabled?: boolean
  onCtaSelect?: (payload: string, label: string) => void
  onCtaPrefill?: (payload: string) => void
}) {
  const quickReplies = actions.filter(isQuickReplyAction)
  const prefills = actions.filter(isPrefillAction)
  const hasActions = quickReplies.length > 0 || prefills.length > 0
  const chipClass =
    'rounded-full border px-3 py-1.5 text-xs font-medium shadow-sm motion-safe:transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'

  return (
    <div className="flex justify-start">
      <div className="max-w-[90%]">
        <Bubble role="assist" text={text} />
        {hasActions ? (
          <div className="mt-2 pl-1">
            <p className="mb-1.5 text-[10px] font-medium text-muted-foreground">
              {actionsEnabled ? 'Suggested replies — tap to send' : 'CTA options offered'}
            </p>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Suggested replies">
              {quickReplies.map((action, index) => (
                <button
                  key={`${action.id}-${index}`}
                  type="button"
                  disabled={!actionsEnabled}
                  onClick={() => onCtaSelect?.(action.payload, action.label)}
                  className={cn(
                    chipClass,
                    actionsEnabled
                      ? 'cursor-pointer border-primary/20 bg-primary/[0.08] text-foreground ring-1 ring-primary/10 hover:border-primary/35 hover:bg-primary/[0.14]'
                      : 'cursor-default border-border/60 bg-muted/30 text-muted-foreground',
                  )}
                >
                  {action.label}
                </button>
              ))}
              {prefills.map((action, index) => (
                <button
                  key={`${action.id}-${index}`}
                  type="button"
                  disabled={!actionsEnabled}
                  onClick={() => onCtaPrefill?.(action.payload)}
                  className={cn(
                    chipClass,
                    actionsEnabled
                      ? 'cursor-pointer border-border/80 bg-muted/40 text-foreground hover:border-primary/25 hover:bg-muted/70'
                      : 'cursor-default border-border/60 bg-muted/30 text-muted-foreground',
                  )}
                  title={actionsEnabled ? 'Fill the message box — edit before sending' : undefined}
                >
                  {action.label}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
