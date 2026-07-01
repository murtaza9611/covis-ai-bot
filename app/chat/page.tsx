'use client'

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type FormEvent,
} from 'react'
import { toast } from 'sonner'
import { ChatMessage } from '@/components/chat-message'
import { ChatInput } from '@/components/chat-input'
import { ChatEmptyState } from '@/components/chat-empty-state'
import { ChatTypingIndicator } from '@/components/chat-typing-indicator'
import { ChatPageHeader } from '@/components/chat-page-header'
import type { ChatApiHealth } from '@/components/status-pill'
import { TopBar } from '@/components/top-bar'
import { Sidebar } from '@/components/sidebar'
import { MobileNavSheet } from '@/components/mobile-nav-sheet'
import type { SimpleChatMessage } from '@/lib/chat-mock'
import { parseChatReply } from '@/lib/covis-api'
import { useSessionId } from '@/hooks/use-session-id'
import { useVisualViewportInset } from '@/hooks/use-visual-viewport-inset'

export default function ChatPage() {
  const [localInput, setLocalInput] = useState('')
  const [navOpen, setNavOpen] = useState(false)
  const [messages, setMessages] = useState<SimpleChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [timezone, setTimezone] = useState('UTC')
  const [apiHealth, setApiHealth] = useState<ChatApiHealth>('idle')
  const threadRef = useRef<HTMLDivElement>(null)
  const threadEndRef = useRef<HTMLDivElement>(null)
  const isNearBottomRef = useRef(true)
  const forceStickToBottomRef = useRef(true)
  const sessionId = useSessionId()
  const vvKeyboardInset = useVisualViewportInset()

  useEffect(() => {
    try {
      setTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC')
    } catch {
      setTimezone('UTC')
    }
  }, [])

  const updateNearBottom = useCallback(() => {
    const el = threadRef.current
    if (!el) return
    const remaining = el.scrollHeight - el.scrollTop - el.clientHeight
    isNearBottomRef.current = remaining < 96
  }, [])

  const scrollThreadEnd = useCallback(() => {
    const el = threadRef.current
    const end = threadEndRef.current
    if (!el || !end) return
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const coarsePointer = window.matchMedia('(pointer: coarse)').matches
    end.scrollIntoView({
      block: 'end',
      behavior: reduceMotion || coarsePointer ? 'auto' : 'smooth',
    })
  }, [])

  useEffect(() => {
    const shouldStick = forceStickToBottomRef.current || isNearBottomRef.current
    if (!shouldStick) return

    const raf = requestAnimationFrame(() => {
      scrollThreadEnd()
    })
    // Mobile keyboards (especially iOS) resize visual viewport in phases.
    // Follow-up snaps keep the thread pinned to the latest message.
    const settleFast = window.setTimeout(() => {
      scrollThreadEnd()
    }, 120)
    const settleSlow = window.setTimeout(() => {
      scrollThreadEnd()
      if (!isLoading) {
        forceStickToBottomRef.current = false
      }
    }, 320)
    return () => {
      cancelAnimationFrame(raf)
      window.clearTimeout(settleFast)
      window.clearTimeout(settleSlow)
    }
  }, [messages.length, isLoading, vvKeyboardInset, scrollThreadEnd])

  useEffect(() => {
    const el = threadRef.current
    if (!el) return
    updateNearBottom()
  }, [updateNearBottom, messages.length])

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || isLoading) return
      forceStickToBottomRef.current = true

      const userMsg: SimpleChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        text: trimmed,
      }
      setMessages((prev) => [...prev, userMsg])
      setIsLoading(true)

      try {
        const res = await fetch('/api/covis-chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: trimmed,
            timezone,
            session_id: sessionId,
          }),
        })

        const data: unknown = await res.json().catch(() => ({}))

        if (!res.ok) {
          const errMsg =
            typeof data === 'object' &&
            data !== null &&
            'error' in data &&
            typeof (data as { error: unknown }).error === 'string'
              ? (data as { error: string }).error
              : `Request failed (${res.status})`
          toast.error(errMsg)
          setApiHealth('error')
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: 'assistant',
              text: errMsg,
              isError: true,
            },
          ])
          return
        }

        const parsed = parseChatReply(data)
        const assistantText =
          parsed?.reply.trim() ??
          (typeof data === 'object' && data !== null
            ? JSON.stringify(data)
            : 'Received a response we could not display.')

        setApiHealth('ok')
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            text: assistantText,
            actions: parsed?.actions,
            responseKind: parsed?.responseKind,
            isError: !parsed?.reply.trim(),
          },
        ])
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Network error'
        toast.error(msg)
        setApiHealth('error')
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            text: msg,
            isError: true,
          },
        ])
      } finally {
        setIsLoading(false)
      }
    },
    [isLoading, sessionId, timezone],
  )

  const handleFormSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const text = localInput.trim()
    if (!text || isLoading) return
    setLocalInput('')
    await sendMessage(text)
  }

  const handleActionSelect = useCallback(
    (payload: string) => {
      void sendMessage(payload)
    },
    [sendMessage],
  )

  const handleActionPrefill = useCallback((payload: string) => {
    setLocalInput(payload)
    forceStickToBottomRef.current = true
  }, [])

  const latestAssistantId = [...messages]
    .reverse()
    .find((m) => m.role === 'assistant')?.id

  return (
    <div
      className="canvas-chat-pattern relative flex min-h-0 flex-col overflow-hidden"
      style={
        {
          '--vv-keyboard-inset': `${vvKeyboardInset}px`,
          height: 'calc(100dvh - var(--vv-keyboard-inset, 0px))',
          minHeight: 'calc(100svh - var(--vv-keyboard-inset, 0px))',
        } as CSSProperties
      }
    >
      <a
        href="#chat-main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2.5 focus:text-sm focus:font-medium focus:text-primary-foreground focus:shadow-md"
      >
        Skip to chat
      </a>

      <TopBar onOpenMobileMenu={() => setNavOpen(true)} apiHealth={apiHealth} />

      <MobileNavSheet open={navOpen} onOpenChange={setNavOpen} />

      <div className="flex min-h-0 flex-1 md:gap-3 md:pl-3 md:pr-4 md:pb-4 md:pt-2">
        <Sidebar className="hidden md:flex" />

        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <main
            id="chat-main"
            aria-label="Bug reporting chat"
            className="flex min-h-0 flex-1 flex-col overflow-hidden"
          >
            {/* <ChatPageHeader /> */}

            <div className="flex min-h-0 flex-1 flex-col px-4 pb-2 pt-4 md:px-8 md:pb-4 md:pt-8">
              <div className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col">
                <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-border/70 bg-card/95 shadow-chat-card ring-1 ring-zinc-900/5 motion-safe:transition-shadow motion-safe:duration-300 motion-safe:hover:shadow-lg motion-safe:hover:ring-primary/10 dark:ring-white/[0.06]">
                  <div
                    className="pointer-events-none absolute inset-x-0 top-0 z-10 h-8 bg-gradient-to-b from-card from-70% to-transparent md:h-10"
                    aria-hidden
                  />
                  <div
                    ref={threadRef}
                    className="chat-thread-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-6 md:px-8 md:py-8"
                    onScroll={updateNearBottom}
                    aria-live="polite"
                    aria-relevant="additions"
                  >
                    <div className="mx-auto w-full max-w-2xl space-y-0">
                      {messages.length === 0 ? (
                        <ChatEmptyState onPick={(t) => setLocalInput(t)} />
                      ) : (
                        <>
                          {messages.map((message) => (
                            <ChatMessage
                              key={message.id}
                              message={message}
                              onActionSelect={handleActionSelect}
                              onActionPrefill={handleActionPrefill}
                              actionsEnabled={
                                !isLoading &&
                                message.role === 'assistant' &&
                                message.id === latestAssistantId
                              }
                            />
                          ))}
                          {isLoading ? <ChatTypingIndicator /> : null}
                        </>
                      )}
                      <div ref={threadEndRef} className="h-px w-full" aria-hidden />
                    </div>
                  </div>
                  <div
                    className="pointer-events-none absolute inset-x-0 bottom-0 z-10 h-8 bg-gradient-to-t from-card from-70% to-transparent md:h-10"
                    aria-hidden
                  />
                </div>
              </div>
            </div>

            <ChatInput
              value={localInput}
              onChange={setLocalInput}
              onSubmit={handleFormSubmit}
              isSending={isLoading}
            />
          </main>
        </div>
      </div>
    </div>
  )
}
