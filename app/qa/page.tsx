'use client'

import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { toast } from 'sonner'
import { TopBar } from '@/components/top-bar'
import { Sidebar } from '@/components/sidebar'
import { MobileNavSheet } from '@/components/mobile-nav-sheet'
import { ChatInput } from '@/components/chat-input'
import { QASessionConfig } from '@/components/qa/qa-session-config'
import { QATranscript } from '@/components/qa/qa-transcript'
import { QAReport } from '@/components/qa/qa-report'
import {
  getQASession,
  sendQAMessage,
  startQASession,
  stopQASession,
  type QADriveMode,
  type QAMode,
  type QASessionStatus,
  type QASessionStatusData,
} from '@/lib/covis-qa-api'

const POLL_INTERVAL_MS = 2000

export default function QAPage() {
  const [navOpen, setNavOpen] = useState(false)
  const [mode, setMode] = useState<QAMode>('POSITIVE')
  const [driveMode, setDriveMode] = useState<QADriveMode>('AUTO')
  const [maxTurns, setMaxTurns] = useState(10)
  const [timezone, setTimezone] = useState('UTC')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [status, setStatus] = useState<QASessionStatus | 'idle'>('idle')
  const [sessionData, setSessionData] = useState<QASessionStatusData | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [isStopping, setIsStopping] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [manualInput, setManualInput] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    try {
      setTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC')
    } catch {
      setTimezone('UTC')
    }
  }, [])

  const applySessionData = useCallback((data: QASessionStatusData) => {
    setSessionData(data)
    setStatus(data.status)
  }, [])

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const pollSession = useCallback(
    async (id: string) => {
      try {
        const data = await getQASession(id)
        if (!data) return
        applySessionData(data)
        if (data.status !== 'running') {
          stopPolling()
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'Poll failed'
        toast.error(msg)
        stopPolling()
      }
    },
    [applySessionData, stopPolling],
  )

  const startPolling = useCallback(
    (id: string) => {
      stopPolling()
      void pollSession(id)
      pollRef.current = setInterval(() => {
        void pollSession(id)
      }, POLL_INTERVAL_MS)
    },
    [pollSession, stopPolling],
  )

  useEffect(() => {
    return () => stopPolling()
  }, [stopPolling])

  const handleStart = useCallback(async () => {
    setIsStarting(true)
    try {
      const data = await startQASession({ mode, driveMode, maxTurns, timezone })
      if (!data) {
        toast.error('Failed to start QA session')
        return
      }
      setSessionId(data.qa_session_id)
      setManualInput('')
      setSessionData({
        qa_session_id: data.qa_session_id,
        mode: data.mode,
        drive_mode: data.drive_mode,
        max_turns: data.max_turns,
        current_turn: 0,
        status: 'running',
        turns: [],
        banner: data.banner,
        task_count: data.task_count,
      })
      setStatus('running')
      toast.success(
        data.drive_mode === 'AUTO' ? 'Auto QA session started' : 'Manual QA session started',
      )
      if (data.drive_mode === 'AUTO') {
        startPolling(data.qa_session_id)
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Start failed'
      toast.error(msg)
    } finally {
      setIsStarting(false)
    }
  }, [mode, driveMode, maxTurns, timezone, startPolling])

  const handleStop = useCallback(async () => {
    if (!sessionId) return
    setIsStopping(true)
    stopPolling()
    try {
      const data = await stopQASession(sessionId)
      if (data) {
        applySessionData(data)
        toast.success('QA session stopped')
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Stop failed'
      toast.error(msg)
      if (sessionData?.drive_mode === 'AUTO') {
        startPolling(sessionId)
      }
    } finally {
      setIsStopping(false)
    }
  }, [sessionId, stopPolling, startPolling, applySessionData, sessionData?.drive_mode])

  const handleManualSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault()
      const text = manualInput.trim()
      if (!text || !sessionId || isSending) return

      setIsSending(true)
      setManualInput('')
      try {
        const data = await sendQAMessage(sessionId, text, { source: 'text' })
        if (data) {
          applySessionData(data)
          if (data.status !== 'running') {
            toast.success('Session complete — report ready')
          }
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Send failed'
        toast.error(msg)
        setManualInput(text)
      } finally {
        setIsSending(false)
      }
    },
    [manualInput, sessionId, isSending, applySessionData],
  )

  const handleCtaSelect = useCallback(
    async (payload: string, label: string) => {
      const text = payload.trim()
      if (!text || !sessionId || isSending) return

      setIsSending(true)
      try {
        const data = await sendQAMessage(sessionId, text, { source: 'cta', ctaLabel: label })
        if (data) {
          applySessionData(data)
          if (data.status !== 'running') {
            toast.success('Session complete — report ready')
          }
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Send failed'
        toast.error(msg)
      } finally {
        setIsSending(false)
      }
    },
    [sessionId, isSending, applySessionData],
  )

  const handleCtaPrefill = useCallback((payload: string) => {
    setManualInput(payload)
  }, [])

  const isRunning = status === 'running'
  const activeDriveMode = sessionData?.drive_mode ?? driveMode
  const completedTurns = sessionData?.turns.length ?? 0
  const maxTurnsConfigured = sessionData?.max_turns ?? maxTurns
  const isAutoProcessing =
    activeDriveMode === 'AUTO' && isRunning && completedTurns < maxTurnsConfigured
  const isManualProcessing = activeDriveMode === 'MANUAL' && isSending
  const showManualInput =
    activeDriveMode === 'MANUAL' && isRunning && completedTurns < maxTurnsConfigured

  return (
    <div className="canvas-chat-pattern relative flex h-screen min-h-0 flex-col overflow-hidden">
      <TopBar onOpenMobileMenu={() => setNavOpen(true)} showStatusPill={false} />
      <MobileNavSheet open={navOpen} onOpenChange={setNavOpen} />

      <div className="flex min-h-0 flex-1 md:gap-3 md:pl-3 md:pr-4 md:pb-4 md:pt-2">
        <Sidebar className="hidden md:flex" />

        <main
          id="qa-main"
          aria-label="COVIS QA Agent"
          className="flex min-h-0 min-w-0 flex-1 flex-col gap-2 overflow-hidden px-4 py-2 md:gap-3 md:px-6 md:py-3"
        >
          <div className="shrink-0">
            <QASessionConfig
              mode={mode}
              driveMode={driveMode}
              maxTurns={maxTurns}
              status={status}
              currentTurn={sessionData?.current_turn ?? 0}
              maxTurnsConfigured={maxTurnsConfigured}
              disabled={isStarting || isStopping}
              onModeChange={setMode}
              onDriveModeChange={setDriveMode}
              onMaxTurnsChange={setMaxTurns}
              onStart={() => void handleStart()}
              onStop={() => void handleStop()}
            />
          </div>

          {sessionData?.error ? (
            <p className="shrink-0 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive">
              {sessionData.error}
            </p>
          ) : null}

          <div className="flex min-h-0 flex-1 flex-col gap-2 lg:flex-row lg:gap-3">
            <div className="flex min-h-0 min-w-0 flex-1 flex-col">
              <QATranscript
                banner={sessionData?.banner ?? null}
                turns={sessionData?.turns ?? []}
                isProcessingTurn={isAutoProcessing || isManualProcessing}
                nextTurnNumber={completedTurns + 1}
                driveMode={activeDriveMode}
                isRunning={isRunning}
                ctaActionsEnabled={showManualInput && !isSending}
                onCtaSelect={(payload, label) => void handleCtaSelect(payload, label)}
                onCtaPrefill={handleCtaPrefill}
              />
              {showManualInput ? (
                <div className="shrink-0 border-t border-border/60 pt-2">
                  <ChatInput
                    value={manualInput}
                    onChange={setManualInput}
                    onSubmit={(e) => void handleManualSubmit(e)}
                    isSending={isSending}
                    disabled={isStopping}
                  />
                </div>
              ) : null}
            </div>
            <div className="flex min-h-0 min-w-0 flex-1 flex-col">
              <QAReport
                session={sessionData}
                isRunning={isRunning}
                plainTextReport={sessionData?.report}
              />
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
