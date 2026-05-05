'use client'

import type { ReactNode } from 'react'
import Link from 'next/link'
import { ChevronDown, Menu, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/theme-toggle'
import { StatusPill } from '@/components/status-pill'
import type { ChatApiHealth } from '@/components/status-pill'
import { CovisAssistMark } from '@/components/covis-assist-mark'
import { BRAND_WORD_ACCENT, BRAND_WORD_PRIMARY } from '@/lib/brand'
import { getUserAvatarUrl } from '@/lib/user-avatar'

type TopBarProps = {
  onOpenMobileMenu?: () => void
  /** Defaults to `idle` when omitted (e.g. landing page). */
  apiHealth?: ChatApiHealth
  /** Hide status pill on pages like landing. */
  showStatusPill?: boolean
  /** Extra controls before the account avatar (e.g. “Open chat” on landing). */
  endAccessory?: ReactNode
}

export function TopBar({
  onOpenMobileMenu,
  apiHealth = 'idle',
  showStatusPill = true,
  endAccessory,
}: TopBarProps) {
  return (
    <header className="shrink-0 border-b border-border/70 bg-card/85 shadow-sm backdrop-blur-md supports-[backdrop-filter]:bg-card/75 md:border-border md:bg-card md:shadow-none md:backdrop-blur-none">
      <div className="flex h-14 items-center gap-1.5 px-3 md:h-[4.25rem] md:gap-4 md:px-8">
        {/* Left: mobile menu + brand */}
        <div className="flex min-w-0 shrink-0 items-center gap-1.5 md:gap-3">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-9 w-9 shrink-0 rounded-xl bg-muted/40 motion-safe:transition-colors motion-safe:duration-200 hover:bg-primary/12 md:hidden"
            onClick={onOpenMobileMenu}
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5 text-foreground" />
          </Button>

          <Link
            href="/"
            className="flex min-w-0 items-center gap-1.5 rounded-xl px-1 py-1 outline-none motion-safe:transition-opacity motion-safe:duration-200 hover:opacity-90 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card md:gap-2 md:rounded-lg md:p-0"
            aria-label="Covis Assist — home"
          >
            <div className="hidden h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground md:flex md:h-10 md:w-10">
              <CovisAssistMark className="size-[1.125rem] md:size-5" />
            </div>
            <span className="truncate font-semibold tracking-tight text-foreground max-md:text-sm md:text-lg">
              <span className="text-foreground">{BRAND_WORD_PRIMARY} </span>
              <span className="text-primary">{BRAND_WORD_ACCENT}</span>
            </span>
          </Link>
        </div>

        {/* Center: search */}
        {/* <div className="relative hidden min-w-0 flex-1 md:block">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-primary/65 dark:text-muted-foreground" />
          <input
            type="search"
            placeholder="Search name..."
            className="h-11 w-full max-w-2xl rounded-xl border border-primary/15 bg-primary/[0.06] py-2 pl-11 pr-11 text-sm text-foreground shadow-sm transition-all duration-200 placeholder:text-muted-foreground hover:border-primary/25 hover:bg-primary/[0.1] focus:border-primary/40 focus:bg-card focus:outline-none focus:ring-2 focus:ring-primary/20 lg:max-w-none dark:border-transparent dark:bg-muted/60 dark:hover:border-transparent dark:hover:bg-muted/85 dark:focus:border-primary/35 dark:focus:ring-ring/50"
          />
          <ChevronDown className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-primary/55 dark:text-muted-foreground" />
        </div> */}

        <div className="flex min-w-0 flex-1 justify-center px-0.5 sm:px-3">
          {showStatusPill ? <StatusPill health={apiHealth} /> : null}
        </div>

        {/* Right: theme + optional accessory + avatar */}
        <div className="flex shrink-0 items-center gap-2 md:gap-3">
          <ThemeToggle />
          {endAccessory}
          {/* <button
            type="button"
            className="flex max-w-[10rem] items-center gap-2 rounded-xl border border-transparent bg-secondary/90 px-2 py-1.5 shadow-sm transition-all duration-200 hover:border-primary/15 hover:bg-secondary hover:shadow-md motion-safe:hover:scale-[1.01] sm:max-w-none sm:gap-3 sm:px-4 sm:py-2"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
              C
            </div>
            <div className="min-w-0 text-left">
              <p className="truncate text-xs text-muted-foreground">Current Clinic</p>
              <p className="truncate text-sm font-semibold text-foreground">Naples</p>
            </div>
            <ChevronDown className="hidden h-4 w-4 shrink-0 text-muted-foreground sm:block" />
          </button> */}

          <button
            type="button"
            className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-muted ring-offset-background transition-all duration-200 hover:bg-border hover:ring-2 hover:ring-primary/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Account"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={getUserAvatarUrl()}
              alt=""
              className="h-10 w-10 rounded-full"
              width={40}
              height={40}
            />
          </button>
        </div>
      </div>

      {/* <div className="border-t border-border px-4 pb-3 pt-2 md:hidden">
        <div className="relative">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-primary/65 dark:text-muted-foreground" />
          <input
            type="search"
            placeholder="Search name..."
            className="h-11 w-full rounded-xl border border-primary/15 bg-primary/[0.06] py-2 pl-11 pr-11 text-sm text-foreground shadow-sm transition-all duration-200 placeholder:text-muted-foreground hover:border-primary/25 hover:bg-primary/[0.1] focus:border-primary/40 focus:bg-card focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-transparent dark:bg-muted/60 dark:hover:border-transparent dark:hover:bg-muted/85 dark:focus:border-primary/35 dark:focus:ring-ring/50"
          />
          <ChevronDown className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-primary/55 dark:text-muted-foreground" />
        </div>
      </div> */}
    </header>
  )
}
