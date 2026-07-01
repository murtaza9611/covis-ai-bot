/** Covis chat CTA action types. */
export type ChatActionType = 'quick_reply' | 'prefill'

/** Covis chat API action (quick reply or prefill). */
export type ChatAction = {
  id: string
  label: string
  type: ChatActionType
  payload: string
}

/** Parsed assistant reply from Covis chat API. */
export type ChatReplyData = {
  reply: string
  actions: ChatAction[]
  responseKind: string
  tasks: Record<string, unknown>[]
}

function normalizeActionType(raw: unknown): ChatActionType | null {
  if (raw === 'prefill') return 'prefill'
  if (raw === 'hint' || raw === 'free_text_hint') return null
  return 'quick_reply'
}

function parseAction(item: unknown): ChatAction | null {
  if (!item || typeof item !== 'object') return null
  const o = item as Record<string, unknown>
  if (typeof o.id !== 'string' || typeof o.label !== 'string') return null
  const type = normalizeActionType(o.type)
  if (!type) return null
  return {
    id: o.id,
    label: o.label,
    type,
    payload: typeof o.payload === 'string' ? o.payload : '',
  }
}

/** Sends payload immediately when tapped. */
export function isQuickReplyAction(action: ChatAction): boolean {
  return action.type === 'quick_reply' && action.payload.trim().length > 0
}

/** Fills the chat input for the user to edit before sending. */
export function isPrefillAction(action: ChatAction): boolean {
  return action.type === 'prefill' && action.payload.trim().length > 0
}

/** @deprecated Use isQuickReplyAction */
export function isClickableAction(action: ChatAction): boolean {
  return isQuickReplyAction(action)
}

export function partitionActions(actions: ChatAction[] | undefined) {
  const list = actions ?? []
  return {
    quickReplies: list.filter(isQuickReplyAction),
    prefills: list.filter(isPrefillAction),
  }
}

function dedupeActions(actions: ChatAction[]): ChatAction[] {
  const seen = new Set<string>()
  const result: ChatAction[] = []
  for (const action of actions) {
    const key = `${action.type}:${action.payload.toLowerCase()}:${action.id}`
    if (seen.has(key)) continue
    seen.add(key)
    result.push(action)
  }
  return result
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
    const actions = dedupeActions(
      Array.isArray(d.actions)
        ? d.actions.map(parseAction).filter((a): a is ChatAction => a !== null)
        : [],
    )
    const responseKind =
      typeof d.response_kind === 'string' ? d.response_kind : 'text'
    const filteredActions =
      responseKind === 'clarify'
        ? actions.filter((a) => a.type !== 'prefill')
        : actions
    const tasks = Array.isArray(d.tasks)
      ? d.tasks.filter(
          (t): t is Record<string, unknown> =>
            typeof t === 'object' && t !== null,
        )
      : []

    if (reply.trim() || filteredActions.length > 0) {
      return { reply, actions: filteredActions, responseKind, tasks }
    }

    const inner =
      d.message ?? d.response ?? d.text ?? d.content
    if (typeof inner === 'string' && inner.trim()) {
      return {
        reply: inner,
        actions: filteredActions,
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
