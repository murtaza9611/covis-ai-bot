/** Covis chat API action (quick reply / hint). */
export type ChatAction = {
  id: string
  label: string
  type: string
  payload: string
}

/** Parsed assistant reply from Covis chat API. */
export type ChatReplyData = {
  reply: string
  actions: ChatAction[]
  responseKind: string
  tasks: Record<string, unknown>[]
}

function parseAction(item: unknown): ChatAction | null {
  if (!item || typeof item !== 'object') return null
  const o = item as Record<string, unknown>
  if (typeof o.id !== 'string' || typeof o.label !== 'string') return null
  return {
    id: o.id,
    label: o.label,
    type: typeof o.type === 'string' ? o.type : 'quick_reply',
    payload: typeof o.payload === 'string' ? o.payload : '',
  }
}

export function isClickableAction(action: ChatAction): boolean {
  return action.type !== 'free_text_hint' && action.payload.trim().length > 0
}

/** Parse Covis chat API envelope into structured reply data. */
export function parseChatReply(payload: unknown): ChatReplyData | null {
  if (payload === null || payload === undefined) return null
  if (typeof payload === 'string') {
    return { reply: payload, actions: [], responseKind: 'text', tasks: [] }
  }
  if (typeof payload !== 'object') return null

  const o = payload as Record<string, unknown>

  // Covis envelope: reply text is in `data.reply`; top-level `message` is status only.
  if (typeof o.data === 'object' && o.data !== null) {
    const d = o.data as Record<string, unknown>
    const reply = typeof d.reply === 'string' ? d.reply : ''
    const actions = Array.isArray(d.actions)
      ? d.actions.map(parseAction).filter((a): a is ChatAction => a !== null)
      : []
    const responseKind =
      typeof d.response_kind === 'string' ? d.response_kind : 'text'
    const tasks = Array.isArray(d.tasks)
      ? d.tasks.filter(
          (t): t is Record<string, unknown> =>
            typeof t === 'object' && t !== null,
        )
      : []

    if (reply.trim() || actions.length > 0) {
      return { reply, actions, responseKind, tasks }
    }

    const inner =
      d.message ?? d.response ?? d.text ?? d.content
    if (typeof inner === 'string' && inner.trim()) {
      return {
        reply: inner,
        actions,
        responseKind,
        tasks,
      }
    }
  }

  if (typeof o.data === 'string' && o.data.trim()) {
    return { reply: o.data, actions: [], responseKind: 'text', tasks: [] }
  }

  const direct = o.response ?? o.reply ?? o.answer ?? o.text ?? o.content
  if (typeof direct === 'string' && direct.trim()) {
    return { reply: direct, actions: [], responseKind: 'text', tasks: [] }
  }

  if (Array.isArray(o.choices) && o.choices[0]) {
    const c = o.choices[0] as Record<string, unknown>
    const msg = c.message as Record<string, unknown> | undefined
    const content =
      msg && typeof msg.content === 'string'
        ? msg.content
        : typeof c.text === 'string'
          ? c.text
          : null
    if (content?.trim()) {
      return { reply: content, actions: [], responseKind: 'text', tasks: [] }
    }
  }

  return null
}

/** Normalize Covis chat API JSON to assistant reply text. */
export function extractAssistantText(payload: unknown): string | null {
  const parsed = parseChatReply(payload)
  if (parsed?.reply.trim()) return parsed.reply
  return null
}
