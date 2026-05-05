/** Normalize Covis chat API JSON — shape may vary by version. */
export function extractAssistantText(payload: unknown): string | null {
  if (payload === null || payload === undefined) return null
  if (typeof payload === 'string') return payload

  if (typeof payload === 'object') {
    const o = payload as Record<string, unknown>

    // Covis envelope: reply text is in `data`; `message` is a status string only.
    if (typeof o.data === 'string' && o.data.trim()) return o.data

    const direct =
      o.response ?? o.reply ?? o.answer ?? o.text ?? o.content ?? o.message
    if (typeof direct === 'string' && direct.trim()) return direct

    if (typeof o.data === 'object' && o.data !== null) {
      const d = o.data as Record<string, unknown>
      const inner =
        d.message ?? d.response ?? d.reply ?? d.text ?? d.content
      if (typeof inner === 'string' && inner.trim()) return inner
    }

    if (Array.isArray(o.choices) && o.choices[0]) {
      const c = o.choices[0] as Record<string, unknown>
      const msg = c.message as Record<string, unknown> | undefined
      if (msg && typeof msg.content === 'string') return msg.content
      if (typeof c.text === 'string') return c.text
    }
  }

  return null
}
