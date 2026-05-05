export type ChatRole = 'user' | 'assistant'

export type SimpleChatMessage = {
  id: string
  role: ChatRole
  text: string
  /** Set when the message is an error notice from the assistant role. */
  isError?: boolean
}

/** Static transcript — matches product reference / design mock. */
export const MOCK_CONVERSATION: SimpleChatMessage[] = [
  {
    id: 'm1',
    role: 'assistant',
    text: "Hi there! I'm the Bug Reporting Assistant. What issue would you like to report today?",
  },
  { id: 'm2', role: 'user', text: 'hey mann' },
  { id: 'm3', role: 'user', text: "what's up" },
  { id: 'm4', role: 'user', text: 'hi' },
]
