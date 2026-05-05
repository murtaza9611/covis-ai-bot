'use client'

import { Toaster as SonnerToaster } from 'sonner'
import { useTheme } from 'next-themes'
import { useEffect, useState } from 'react'

export function AppToaster() {
  const { resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const sonnerTheme =
    !mounted ? 'system' : resolvedTheme === 'dark' ? 'dark' : 'light'

  return (
    <SonnerToaster
      position="top-center"
      richColors
      closeButton
      theme={sonnerTheme}
    />
  )
}
