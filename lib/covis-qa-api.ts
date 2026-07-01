export type QAMode = 'POSITIVE' | 'NEGATIVE'
export type QADriveMode = 'AUTO' | 'MANUAL'
export type QASessionStatus = 'running' | 'stopped' | 'completed' | 'failed'
export type QAMessageSource = 'text' | 'cta'

export type QAChatAction = {
  id: string
  label: string
  type: string
  payload: string
}

export type TurnGrade = {
  relevance: number
  accuracy: number
  tone: number
  completeness: number
  cta_relevance?: number | null
  cta_quality?: number | null
  weighted_score: number
  classification: 'issue' | 'suggestion'
  what_went_wrong?: string | null
  expected_reply?: string | null
  prompt_fix?: string | null
  what_could_be_better?: string | null
  prompt_enhancement?: string | null
  cta_feedback?: string | null
  capability_tag?: string | null
  adversarial_tag?: string | null
}

export type QATurnRecord = {
  turn_number: number
  client_message: string
  client_message_source?: QAMessageSource
  client_cta_label?: string | null
  bot_reply: string
  bot_actions?: QAChatAction[]
  grade: TurnGrade
}

export type QASessionStartData = {
  qa_session_id: string
  banner: string
  task_count: number
  mode: QAMode
  drive_mode: QADriveMode
  max_turns: number
}

export type QASessionStatusData = {
  qa_session_id: string
  mode: QAMode
  drive_mode: QADriveMode
  max_turns: number
  current_turn: number
  status: QASessionStatus
  turns: QATurnRecord[]
  report?: string | null
  error?: string | null
  banner?: string | null
  task_count?: number
}

type ApiEnvelope<T> = {
  data?: T
  succeeded?: boolean
  message?: string
}

function parseEnvelope<T>(payload: unknown): T | null {
  if (!payload || typeof payload !== 'object') return null
  const o = payload as ApiEnvelope<T>
  return o.data ?? null
}

export async function startQASession(opts: {
  mode: QAMode
  driveMode: QADriveMode
  maxTurns: number
  timezone: string
}): Promise<QASessionStartData | null> {
  const res = await fetch('/api/covis-qa/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({
      mode: opts.mode,
      drive_mode: opts.driveMode,
      max_turns: opts.maxTurns,
      timezone: opts.timezone,
    }),
  })
  const json = await res.json()
  if (!res.ok) {
    throw new Error(
      typeof json?.message === 'string' ? json.message : 'Failed to start QA session',
    )
  }
  return parseEnvelope<QASessionStartData>(json)
}

export async function getQASession(
  qaSessionId: string,
): Promise<QASessionStatusData | null> {
  const res = await fetch(`/api/covis-qa/sessions/${qaSessionId}`, {
    headers: { accept: 'application/json' },
  })
  const json = await res.json()
  if (!res.ok) {
    throw new Error(
      typeof json?.message === 'string' ? json.message : 'Failed to fetch QA session',
    )
  }
  return parseEnvelope<QASessionStatusData>(json)
}

export async function sendQAMessage(
  qaSessionId: string,
  message: string,
  opts?: { source?: QAMessageSource; ctaLabel?: string },
): Promise<QASessionStatusData | null> {
  const res = await fetch(`/api/covis-qa/sessions/${qaSessionId}/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({
      message,
      source: opts?.source ?? 'text',
      cta_label: opts?.ctaLabel ?? null,
    }),
  })
  const json = await res.json()
  if (!res.ok) {
    throw new Error(
      typeof json?.message === 'string' ? json.message : 'Failed to send message',
    )
  }
  return parseEnvelope<QASessionStatusData>(json)
}

export async function stopQASession(
  qaSessionId: string,
): Promise<QASessionStatusData | null> {
  const res = await fetch(`/api/covis-qa/sessions/${qaSessionId}/stop`, {
    method: 'POST',
    headers: { accept: 'application/json' },
  })
  const json = await res.json()
  if (!res.ok) {
    throw new Error(
      typeof json?.message === 'string' ? json.message : 'Failed to stop QA session',
    )
  }
  return parseEnvelope<QASessionStatusData>(json)
}

export function scoreBadgeClass(score: number): string {
  if (score >= 80) return 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400'
  if (score >= 60) return 'bg-amber-500/15 text-amber-700 dark:text-amber-400'
  return 'bg-red-500/15 text-red-700 dark:text-red-400'
}
