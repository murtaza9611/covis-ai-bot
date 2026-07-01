'use client'

import { useCallback, useMemo, useState, type ComponentType } from 'react'
import {
  AlertTriangle,
  BarChart3,
  Check,
  CheckCircle2,
  ClipboardList,
  Copy,
  Lightbulb,
  Target,
  XCircle,
} from 'lucide-react'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { QASessionStatusData } from '@/lib/covis-qa-api'
import { scoreBadgeClass } from '@/lib/covis-qa-api'
import {
  computeSessionSummary,
  getNegativeCoverage,
  getPositiveCoverage,
  getRecommendedPatches,
  getTopIssues,
  modeLabel,
  overallScoreColor,
} from '@/lib/qa-report-utils'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

type QAReportProps = {
  session: QASessionStatusData | null | undefined
  isRunning?: boolean
  plainTextReport?: string | null
}

export function QAReport({ session, isRunning = false, plainTextReport }: QAReportProps) {
  const [copied, setCopied] = useState(false)

  const summary = useMemo(
    () =>
      session
        ? computeSessionSummary(session.turns, session.max_turns)
        : null,
    [session],
  )

  const topIssues = useMemo(
    () => (session ? getTopIssues(session.turns) : []),
    [session],
  )

  const patches = useMemo(
    () => (session ? getRecommendedPatches(session.turns) : []),
    [session],
  )

  const coverage = useMemo(() => {
    if (!session) return []
    return session.mode === 'POSITIVE'
      ? getPositiveCoverage(session.turns)
      : getNegativeCoverage(session.turns)
  }, [session])

  const handleCopy = useCallback(async () => {
    const text = plainTextReport ?? ''
    if (!text) return
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      toast.success('Report copied to clipboard')
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error('Could not copy report')
    }
  }, [plainTextReport])

  const hasReport =
    !!session && !isRunning && !!session.report && session.turns.length > 0

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-border/70 bg-card/95 shadow-sm ring-1 ring-black/[0.03] dark:ring-white/[0.06]">
      <div className="flex shrink-0 items-center justify-between border-b border-border/60 px-3 py-2">
        <h2 className="text-sm font-semibold">Session report</h2>
        {plainTextReport ? (
          <Button type="button" variant="outline" size="sm" onClick={() => void handleCopy()}>
            {copied ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
            Copy plain text
          </Button>
        ) : null}
      </div>

      <div className="chat-thread-scroll flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain">
        {!hasReport || !summary ? (
          <div className="flex min-h-full flex-1 items-center justify-center p-3">
            <ReportEmptyState session={session} isRunning={isRunning} />
          </div>
        ) : (
          <div className="space-y-6 p-3">
            <ReportHeader session={session} summary={summary} />

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatCard label="Overall score" value={`${summary.overallScore}`} suffix="/100" valueClass={overallScoreColor(summary.overallScore)} />
              <StatCard label="Passed" value={String(summary.passed)} suffix="turns" accent="emerald" />
              <StatCard label="Failed" value={String(summary.failed)} suffix="turns" accent="red" />
              <StatCard label="Completed" value={`${summary.turnsCompleted}/${summary.maxTurns}`} suffix="turns" />
            </div>

            {topIssues.length > 0 ? (
              <section className="space-y-3">
                <SectionTitle icon={AlertTriangle} title="Top issues" />
                <ul className="space-y-2">
                  {topIssues.map((turn) => (
                    <li
                      key={turn.turn_number}
                      className="rounded-xl border border-red-500/20 bg-red-500/5 p-3 dark:bg-red-500/10"
                    >
                      <div className="mb-1 flex flex-wrap items-center gap-2">
                        <Badge variant="destructive" className="text-[10px]">
                          Turn {turn.turn_number}
                        </Badge>
                        <span className={cn('text-xs font-semibold tabular-nums', scoreBadgeClass(turn.grade.weighted_score))}>
                          {turn.grade.weighted_score.toFixed(0)}/100
                        </span>
                      </div>
                      <p className="text-sm text-foreground">
                        {turn.grade.what_went_wrong ?? 'Reply did not meet quality threshold.'}
                      </p>
                      {turn.grade.prompt_fix ? (
                        <p className="mt-2 text-xs text-muted-foreground">
                          <span className="font-medium text-foreground">Fix: </span>
                          {turn.grade.prompt_fix}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </section>
            ) : (
              <div className="flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3 text-sm text-emerald-800 dark:text-emerald-300">
                <CheckCircle2 className="size-4 shrink-0" aria-hidden />
                No critical issues — all turns scored ≥80.
              </div>
            )}

            <section className="space-y-3">
              <SectionTitle icon={Lightbulb} title="Recommended prompt patches" />
              <ol className="space-y-2">
                {patches.map((patch, i) => (
                  <li
                    key={i}
                    className="rounded-lg border border-border/60 border-l-4 border-l-primary bg-muted/30 px-3 py-2.5 text-sm leading-relaxed"
                  >
                    <span className="mr-2 font-semibold text-primary">{i + 1}.</span>
                    {patch}
                  </li>
                ))}
              </ol>
            </section>

            <section className="space-y-3">
              <SectionTitle
                icon={Target}
                title={session.mode === 'POSITIVE' ? 'Capability coverage' : 'Adversarial coverage'}
              />
              <ul className="grid gap-2 sm:grid-cols-2">
                {coverage.map((item) => (
                  <CoverageRow key={item.label} item={item} mode={session.mode} />
                ))}
              </ul>
            </section>

            <section className="space-y-3">
              <SectionTitle icon={CheckCircle2} title="Turn-by-turn breakdown" />
              <Accordion type="multiple" className="rounded-xl border border-border/60 px-1">
                {session.turns.map((turn) => (
                  <AccordionItem key={turn.turn_number} value={`turn-${turn.turn_number}`}>
                    <AccordionTrigger className="px-3 py-3 hover:no-underline">
                      <div className="flex flex-1 items-center gap-2 text-left">
                        <span className="text-sm font-medium">Turn {turn.turn_number}</span>
                        <span
                          className={cn(
                            'rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums',
                            scoreBadgeClass(turn.grade.weighted_score),
                          )}
                        >
                          {turn.grade.weighted_score.toFixed(0)}/100
                        </span>
                        <Badge
                          variant={turn.grade.classification === 'issue' ? 'destructive' : 'secondary'}
                          className="ml-auto mr-2 text-[10px]"
                        >
                          {turn.grade.classification === 'issue' ? 'Issue' : 'Suggestion'}
                        </Badge>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent className="space-y-3 px-3 pb-4">
                      <MessageBlock
                        label={
                          turn.client_message_source === 'cta'
                            ? `Client (via CTA${turn.client_cta_label ? `: ${turn.client_cta_label}` : ''})`
                            : 'Client'
                        }
                        text={turn.client_message}
                        variant="client"
                      />
                      <MessageBlock label="COVIS Assist" text={turn.bot_reply} variant="assist" />

                      {turn.bot_actions?.length ? (
                        <div className="space-y-2">
                          <p className="text-xs font-semibold text-foreground">CTA options offered</p>
                          <div className="flex flex-wrap gap-2">
                            {turn.bot_actions.map((action) => (
                              <span
                                key={action.id}
                                className="rounded-full border border-border/60 bg-muted/30 px-2.5 py-1 text-[11px] text-muted-foreground"
                              >
                                {action.label}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : null}

                      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                        <ScorePill label="Relevance" value={turn.grade.relevance} />
                        <ScorePill label="Accuracy" value={turn.grade.accuracy} />
                        <ScorePill label="Tone" value={turn.grade.tone} />
                        <ScorePill label="Complete" value={turn.grade.completeness} />
                      </div>

                      {turn.grade.cta_relevance != null && turn.grade.cta_quality != null ? (
                        <div className="grid grid-cols-2 gap-2">
                          <ScorePill label="CTA relevance" value={turn.grade.cta_relevance} />
                          <ScorePill label="CTA quality" value={turn.grade.cta_quality} />
                        </div>
                      ) : null}

                      {turn.grade.classification === 'issue' ? (
                        <DetailBox title="What went wrong" text={turn.grade.what_went_wrong} />
                      ) : (
                        <DetailBox title="What could be better" text={turn.grade.what_could_be_better} />
                      )}

                      {turn.grade.cta_feedback ? (
                        <DetailBox title="CTA feedback" text={turn.grade.cta_feedback} accent />
                      ) : null}

                      {turn.grade.expected_reply ? (
                        <DetailBox title="Expected reply" text={turn.grade.expected_reply} muted />
                      ) : null}

                      {turn.grade.prompt_fix ? (
                        <DetailBox title="Prompt fix" text={turn.grade.prompt_fix} accent />
                      ) : turn.grade.prompt_enhancement ? (
                        <DetailBox title="Prompt enhancement" text={turn.grade.prompt_enhancement} accent />
                      ) : null}
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </section>
          </div>
        )}
      </div>
    </div>
  )
}

function ReportEmptyState({
  session,
  isRunning,
}: {
  session: QASessionStatusData | null | undefined
  isRunning: boolean
}) {
  const isIdle = !session || (!isRunning && session.turns.length === 0 && !session.report)

  if (isRunning && session) {
    const completed = session.turns.length
    const total = session.max_turns
    const driveLabel = session.drive_mode === 'MANUAL' ? 'Manual' : 'Auto'

    return (
      <EmptyStateCard
        icon={BarChart3}
        title="Report in progress"
        description={
          completed > 0
            ? `${completed} of ${total} turns graded so far. Stop the session or finish all turns to unlock scores, issues, and prompt fixes here.`
            : `Your ${driveLabel.toLowerCase()} session is running. Graded results will appear here once you stop or complete all ${total} turns.`
        }
        steps={[
          'Each turn is scored on relevance, accuracy, tone, and completeness',
          'Issues below 80/100 include prompt fix suggestions',
          'Coverage checklist tracks positive or adversarial scenarios',
        ]}
        badge={`${completed}/${total} turns`}
      />
    )
  }

  if (isIdle) {
    return (
      <EmptyStateCard
        icon={ClipboardList}
        title="No report yet"
        description="Start a QA session to evaluate COVIS Assist. When the session ends, you'll get an overall score, turn breakdown, top issues, and copy-paste prompt patches."
        steps={[
          'Auto — agent sends client messages for you',
          'Manual — you type messages; grading stays automatic',
          'Use Stop anytime to generate a report from completed turns',
        ]}
      />
    )
  }

  return (
    <EmptyStateCard
      icon={ClipboardList}
      title="Report unavailable"
      description="This session did not produce a graded report. Start a new session and complete at least one turn."
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
              <span className="mt-1 size-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
              {step}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

function ReportHeader({
  session,
  summary,
}: {
  session: QASessionStatusData
  summary: ReturnType<typeof computeSessionSummary>
}) {
  return (
    <div className="rounded-xl bg-gradient-to-br from-primary/10 via-primary/5 to-transparent p-4 ring-1 ring-primary/10">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            COVIS QA Session Report
          </p>
          <p className={cn('mt-1 text-3xl font-bold tabular-nums', overallScoreColor(summary.overallScore))}>
            {summary.overallScore}
            <span className="text-lg font-semibold text-muted-foreground">/100</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline">{modeLabel(session.mode)} mode</Badge>
          <Badge variant="outline">
            {session.drive_mode === 'AUTO' ? 'Auto drive' : 'Manual drive'}
          </Badge>
          <Badge variant="secondary" className="capitalize">
            {session.status}
          </Badge>
        </div>
      </div>
    </div>
  )
}

function StatCard({
  label,
  value,
  suffix,
  valueClass,
  accent,
}: {
  label: string
  value: string
  suffix?: string
  valueClass?: string
  accent?: 'emerald' | 'red'
}) {
  const accentClass =
    accent === 'emerald'
      ? 'text-emerald-600 dark:text-emerald-400'
      : accent === 'red'
        ? 'text-red-600 dark:text-red-400'
        : undefined

  return (
    <div className="rounded-xl border border-border/60 bg-muted/20 px-3 py-2.5">
      <p className="text-[11px] font-medium text-muted-foreground">{label}</p>
      <p className={cn('mt-0.5 text-xl font-bold tabular-nums', valueClass ?? accentClass)}>
        {value}
        {suffix ? (
          <span className="ml-1 text-xs font-normal text-muted-foreground">{suffix}</span>
        ) : null}
      </p>
    </div>
  )
}

function SectionTitle({
  icon: Icon,
  title,
}: {
  icon: ComponentType<{ className?: string }>
  title: string
}) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="size-4 text-primary" aria-hidden />
      <h3 className="text-sm font-semibold">{title}</h3>
    </div>
  )
}

function CoverageRow({
  item,
  mode,
}: {
  item:
    | { label: string; covered: boolean }
    | { label: string; tested: boolean; handled: boolean | null }
  mode: QASessionStatusData['mode']
}) {
  if (mode === 'POSITIVE' && 'covered' in item) {
    return (
      <li className="flex items-start gap-2 rounded-lg border border-border/50 bg-muted/20 px-3 py-2 text-sm">
        {item.covered ? (
          <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden />
        ) : (
          <XCircle className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
        )}
        <span className={item.covered ? 'text-foreground' : 'text-muted-foreground'}>
          {item.label}
        </span>
      </li>
    )
  }

  if ('tested' in item) {
    return (
      <li className="flex items-start gap-2 rounded-lg border border-border/50 bg-muted/20 px-3 py-2 text-sm">
        {!item.tested ? (
          <XCircle className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
        ) : item.handled ? (
          <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden />
        ) : (
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden />
        )}
        <span>
          {item.label}
          {item.tested ? (
            <span className="ml-1 text-xs text-muted-foreground">
              — {item.handled ? 'handled' : 'struggled'}
            </span>
          ) : (
            <span className="ml-1 text-xs text-muted-foreground">— not tested</span>
          )}
        </span>
      </li>
    )
  }

  return null
}

function MessageBlock({
  label,
  text,
  variant,
}: {
  label: string
  text: string
  variant: 'client' | 'assist'
}) {
  return (
    <div
      className={cn(
        'rounded-lg px-3 py-2.5 text-sm',
        variant === 'client'
          ? 'bg-primary/10 text-foreground'
          : 'border border-border/60 bg-muted/30',
      )}
    >
      <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide opacity-70">
        {label}
      </p>
      <p className="whitespace-pre-wrap leading-relaxed">{text}</p>
    </div>
  )
}

function ScorePill({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-muted/40 px-2 py-1.5 text-center">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold tabular-nums">{value}</p>
    </div>
  )
}

function DetailBox({
  title,
  text,
  muted,
  accent,
}: {
  title: string
  text?: string | null
  muted?: boolean
  accent?: boolean
}) {
  if (!text?.trim()) return null
  return (
    <div
      className={cn(
        'rounded-lg px-3 py-2 text-sm leading-relaxed',
        accent && 'border-l-4 border-l-primary bg-primary/5',
        muted && 'bg-muted/30 italic text-muted-foreground',
        !accent && !muted && 'bg-muted/20',
      )}
    >
      <p className="mb-1 text-xs font-semibold text-foreground">{title}</p>
      <p className={muted ? 'text-muted-foreground' : 'text-foreground'}>{text}</p>
    </div>
  )
}
