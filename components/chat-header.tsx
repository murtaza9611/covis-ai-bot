'use client'

import { User, Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function ChatHeader() {
  return (
    <header className="sticky top-0 z-10 border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
      <div className="flex items-center justify-between px-4 sm:px-6 py-4">
        <div className="flex flex-col gap-0.5">
          <h1 className="text-xl font-semibold text-foreground">Bug Assistant</h1>
          <p className="text-xs text-muted-foreground">Project Clinic • Help & Support</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="h-10 w-10">
            <User className="h-5 w-5 text-muted-foreground" />
          </Button>
          <Button variant="ghost" size="icon" className="h-10 w-10">
            <Menu className="h-5 w-5 text-muted-foreground" />
          </Button>
        </div>
      </div>
    </header>
  )
}
