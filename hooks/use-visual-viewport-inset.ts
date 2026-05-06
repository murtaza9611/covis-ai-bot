'use client'

import { useEffect, useState } from 'react'

/**
 * Pixels of the layout viewport covered below the visual viewport (e.g. software keyboard).
 * Drives `--vv-keyboard-inset` on the chat shell so flex layout matches the visible area.
 * Uses VisualViewport API (iOS Safari 13+, Chromium) with window resize fallback.
 */
function computeBottomInset(): number {
  if (typeof window === 'undefined') return 0
  const vv = window.visualViewport
  if (!vv) return 0
  const inset = window.innerHeight - vv.height - vv.offsetTop
  return Math.max(0, Math.round(inset))
}

export function useVisualViewportInset(): number {
  const [insetPx, setInsetPx] = useState(0)

  useEffect(() => {
    const vv = window.visualViewport

    const update = () => {
      setInsetPx(computeBottomInset())
    }

    update()

    if (vv) {
      vv.addEventListener('resize', update)
      vv.addEventListener('scroll', update)
    }
    window.addEventListener('resize', update)
    window.addEventListener('orientationchange', update)

    return () => {
      if (vv) {
        vv.removeEventListener('resize', update)
        vv.removeEventListener('scroll', update)
      }
      window.removeEventListener('resize', update)
      window.removeEventListener('orientationchange', update)
    }
  }, [])

  return insetPx
}
