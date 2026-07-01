'use client'

import { FlaskConical, Play, ShieldAlert, Square, Sparkles, ThumbsUp, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import type { QADriveMode, QAMode, QASessionStatus } from '@/lib/covis-qa-api'
import { cn } from '@/lib/utils'

type QASessionConfigProps = {
  mode: QAMode
  driveMode: QADriveMode
  maxTurns: number
  status: QASessionStatus | 'idle'
  currentTurn: number
  maxTurnsConfigured: number
  disabled: boolean
  onModeChange: (mode: QAMode) => void
  onDriveModeChange: (driveMode: QADriveMode) => void
  onMaxTurnsChange: (turns: number) => void
  onStart: () => void
  onStop: () => void
}

export function QASessionConfig({
  mode,
  driveMode,
  maxTurns,
  status,
  currentTurn,
  maxTurnsConfigured,
  disabled,
  onModeChange,
  onDriveModeChange,
  onMaxTurnsChange,
  onStart,
  onStop,
}: QASessionConfigProps) {
  const isRunning = status === 'running'

  return (
    <div className="relative overflow-hidden rounded-2xl border border-border/70 bg-card/95 shadow-sm ring-1 ring-black/[0.03] dark:ring-white/[0.06]">
      <div
        className="absolute left-0 top-0 h-full w-1 bg-gradient-to-b from-primary via-primary/90 to-primary/50"
        aria-hidden
      />

      <div className="flex flex-col gap-3 p-3 pl-4 md:p-4 md:pl-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/12 text-primary ring-1 ring-primary/15">
              <FlaskConical className="size-4" aria-hidden />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Quality assurance
              </p>
              <h1 className="text-base font-semibold tracking-tight text-foreground md:text-lg">
                COVIS QA Agent
              </h1>
            </div>
          </div>
          <StatusPill status={status} currentTurn={currentTurn} maxTurns={maxTurnsConfigured} />
        </div>

        <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
          <div className="grid flex-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
            <ControlGroup label="Drive" hint="Who sends client messages">
              <SegmentedControl
                options={[
                  { value: 'AUTO', label: 'Auto', icon: Sparkles },
                  { value: 'MANUAL', label: 'Manual', icon: Zap },
                ]}
                value={driveMode}
                disabled={disabled || isRunning}
                onChange={(v) => onDriveModeChange(v as QADriveMode)}
              />
            </ControlGroup>

            <ControlGroup label="Test mode" hint="Scenario style for this run">
              <SegmentedControl
                options={[
                  { value: 'POSITIVE', label: 'Positive', icon: ThumbsUp },
                  { value: 'NEGATIVE', label: 'Negative', icon: ShieldAlert },
                ]}
                value={mode}
                disabled={disabled || isRunning}
                onChange={(v) => onModeChange(v as QAMode)}
              />
            </ControlGroup>

            <ControlGroup label="Turn budget" hint={`${maxTurns} messages max`}>
              <div className="flex items-center gap-3">
                <input
                  id="max-turns"
                  type="range"
                  min={5}
                  max={20}
                  value={maxTurns}
                  disabled={disabled || isRunning}
                  onChange={(e) => onMaxTurnsChange(Number(e.target.value))}
                  className="h-2 flex-1 cursor-pointer accent-primary"
                  aria-label="Max turns"
                />
                <span className="flex h-7 min-w-[2rem] items-center justify-center rounded-md bg-primary/10 px-1.5 text-xs font-semibold tabular-nums text-primary">
                  {maxTurns}
                </span>
              </div>
            </ControlGroup>
          </div>

          <div className="flex shrink-0 items-center gap-2 lg:pl-2">
            {!isRunning ? (
              <Button
                type="button"
                size="default"
                className="h-10 min-w-[9rem] rounded-xl px-4 shadow-sm"
                onClick={onStart}
                disabled={disabled}
              >
                <Play className="size-4 fill-current" aria-hidden />
                Start session
              </Button>
            ) : (
              <Button
                type="button"
                variant="destructive"
                size="default"
                className="h-10 min-w-[9rem] rounded-xl px-4 shadow-sm"
                onClick={onStop}
              >
                <Square className="size-4 fill-current" aria-hidden />
                Stop session
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function ControlGroup({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div className="rounded-lg border border-border/50 bg-muted/20 px-2.5 py-2">
      <div className="mb-1.5">
        <Label className="text-[11px] font-semibold text-foreground">{label}</Label>
        {hint ? <p className="text-[10px] text-muted-foreground">{hint}</p> : null}
      </div>
      {children}
    </div>
  )
}

function SegmentedControl<T extends string>({
  options,
  value,
  disabled,
  onChange,
}: {
  options: { value: T; label: string; icon?: React.ComponentType<{ className?: string }> }[]
  value: T
  disabled?: boolean
  onChange: (value: T) => void
}) {
  return (
    <div
      className={cn(
        'flex rounded-lg border border-border/60 bg-background/80 p-0.5',
        disabled && 'opacity-60',
      )}
      role="group"
    >
      {options.map(({ value: optValue, label, icon: Icon }) => {
        const selected = value === optValue
        return (
          <button
            key={optValue}
            type="button"
            disabled={disabled}
            aria-pressed={selected}
            onClick={() => onChange(optValue)}
            className={cn(
              'flex flex-1 items-center justify-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium motion-safe:transition-all',
              selected
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground',
              disabled && 'pointer-events-none',
            )}
          >
            {Icon ? <Icon className="size-3.5" aria-hidden /> : null}
            {label}
          </button>
        )
      })}
    </div>
  )
}

function StatusPill({
  status,
  currentTurn,
  maxTurns,
}: {
  status: QASessionStatus | 'idle'
  currentTurn: number
  maxTurns: number
}) {
  const label =
    status === 'idle'
      ? 'Idle'
      : status === 'running'
        ? `Running · ${currentTurn}/${maxTurns}`
        : status.charAt(0).toUpperCase() + status.slice(1)

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium',
        status === 'running' && 'border-primary/25 bg-primary/10 text-primary',
        status === 'completed' && 'border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
        status === 'stopped' && 'border-amber-500/25 bg-amber-500/10 text-amber-700 dark:text-amber-400',
        status === 'failed' && 'border-red-500/25 bg-red-500/10 text-red-700 dark:text-red-400',
        status === 'idle' && 'border-border/60 bg-muted/40 text-muted-foreground',
      )}
    >
      {status === 'running' ? (
        <span className="relative flex size-2">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary/60 opacity-75" />
          <span className="relative inline-flex size-2 rounded-full bg-primary" />
        </span>
      ) : null}
      {label}
    </span>
  )
}
