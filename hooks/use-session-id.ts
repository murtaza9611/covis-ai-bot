'use client'

import { useEffect, useState } from 'react'

const STORAGE_KEY = 'covis_chat_session_id'

export function useSessionId() {
  const [sessionId, setSessionId] = useState<string>('1')

  useEffect(() => {
    try {
      let id = localStorage.getItem(STORAGE_KEY)
      if (!id) {
        id =
          typeof crypto !== 'undefined' && crypto.randomUUID
            ? crypto.randomUUID()
            : `session-${Date.now()}`
        localStorage.setItem(STORAGE_KEY, id)
      }
      setSessionId(id)
    } catch {
      setSessionId(`session-${Date.now()}`)
    }
  }, [])

  return sessionId
}
