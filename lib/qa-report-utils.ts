import type { QAMode, QATurnRecord } from './covis-qa-api'

export const POSITIVE_CAPABILITIES = [
  'Greeting & small talk',
  'Bug logging',
  'Feature request',
  'Duplicate detection',
  'Clarification flow',
  'Project status — broad',
  'Project status — specific task',
  'Assignee query',
  'Due date query',
  'Time-based snapshot',
  'Follow-up in context',
] as const

export const NEGATIVE_ADVERSARIAL_TYPES = [
  'Loop trap',
  'Off-topic / out-of-scope',
  'Scope creep bait',
  'Ambiguous / malformed input',
  'Context hijack',
  'Fake urgency / pressure',
  'Contradictory task report',
  'Follow-up with no prior context',
] as const

export type SessionSummary = {
  overallScore: number
  passed: number
  failed: number
  turnsCompleted: number
  maxTurns: number
}

export function computeSessionSummary(
  turns: QATurnRecord[],
  maxTurns: number,
): SessionSummary {
  const scores = turns.map((t) => t.grade.weighted_score)
  const overallScore =
    scores.length > 0
      ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10
      : 0
  return {
    overallScore,
    passed: scores.filter((s) => s >= 80).length,
    failed: scores.filter((s) => s < 80).length,
    turnsCompleted: turns.length,
    maxTurns,
  }
}

export function getTopIssues(turns: QATurnRecord[]) {
  return turns
    .filter((t) => t.grade.classification === 'issue')
    .sort((a, b) => a.grade.weighted_score - b.grade.weighted_score)
    .slice(0, 10)
}

export function getRecommendedPatches(turns: QATurnRecord[]): string[] {
  const seen = new Set<string>()
  const patches: string[] = []

  for (const turn of getTopIssues(turns)) {
    const fix = turn.grade.prompt_fix?.trim()
    if (fix && !seen.has(fix)) {
      seen.add(fix)
      patches.push(fix)
    }
  }

  if (patches.length === 0) {
    for (const turn of turns) {
      const enh = turn.grade.prompt_enhancement?.trim()
      if (enh && !seen.has(enh)) {
        seen.add(enh)
        patches.push(enh)
        if (patches.length >= 5) break
      }
    }
  }

  if (patches.length === 0) {
    return ['No prompt patches required — session passed all turns.']
  }
  return patches
}

export function getPositiveCoverage(turns: QATurnRecord[]) {
  const covered = new Set(
    turns.map((t) => t.grade.capability_tag).filter(Boolean) as string[],
  )
  return POSITIVE_CAPABILITIES.map((cap) => ({
    label: cap,
    covered: covered.has(cap),
  }))
}

export function getNegativeCoverage(turns: QATurnRecord[]) {
  const tested: Record<string, number[]> = {}
  for (const turn of turns) {
    const tag = turn.grade.adversarial_tag
    if (tag) {
      tested[tag] = tested[tag] ?? []
      tested[tag].push(turn.grade.weighted_score)
    }
  }
  return NEGATIVE_ADVERSARIAL_TYPES.map((adv) => {
    const scores = tested[adv]
    if (!scores?.length) {
      return { label: adv, tested: false as const, handled: null }
    }
    const avg = scores.reduce((a, b) => a + b, 0) / scores.length
    return { label: adv, tested: true as const, handled: avg >= 80 }
  })
}

export function overallScoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-600 dark:text-emerald-400'
  if (score >= 60) return 'text-amber-600 dark:text-amber-400'
  return 'text-red-600 dark:text-red-400'
}

export function modeLabel(mode: QAMode): string {
  return mode === 'POSITIVE' ? 'Positive' : 'Negative'
}
