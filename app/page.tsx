'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ArrowRight, MessageSquare, ShieldCheck, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { TopBar } from '@/components/top-bar'
import { MobileNavSheet } from '@/components/mobile-nav-sheet'
import { BRAND_WORD_ACCENT, BRAND_WORD_PRIMARY } from '@/lib/brand'

const features = [
  {
    icon: MessageSquare,
    title: 'Natural bug reports',
    description:
      'Describe issues in plain language. Covis Assist turns your message into structured context for your team.',
  },
  {
    icon: ShieldCheck,
    title: 'Connected to Covis',
    description:
      'Responses come from your Covis assistant API—same workflows you use for tasks and status.',
  },
  {
    icon: Sparkles,
    title: 'Fast, focused UI',
    description:
      'A minimal chat shell with light/dark themes, ready for production demos and daily use.',
  },
] as const

export default function LandingPage() {
  const [navOpen, setNavOpen] = useState(false)

  return (
    <div className="canvas-chat-pattern relative flex h-screen min-h-0 flex-col overflow-hidden">
      <a
        href="#landing-main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2.5 focus:text-sm focus:font-medium focus:text-primary-foreground focus:shadow-md"
      >
        Skip to content
      </a>

      <TopBar
        onOpenMobileMenu={() => setNavOpen(true)}
        showStatusPill={false}
        // endAccessory={
        //   <Button asChild size="sm" className="shrink-0 rounded-xl px-3 shadow-sm max-sm:h-9 max-sm:px-2.5 max-sm:text-xs">
        //     <Link href="/chat">Open chat</Link>
        //   </Button>
        // }
      />

      <MobileNavSheet open={navOpen} onOpenChange={setNavOpen} />

      <main
        id="landing-main"
        aria-label="Covis Assist overview"
        className="flex min-h-0 flex-1 flex-col overflow-y-auto"
      >
        <div className="flex min-h-0 flex-1 flex-col px-4 pb-3 pt-1 md:px-8 md:pb-4">
          <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col pb-8 pt-6 md:pb-12 md:pt-8">
                <div className="mx-auto max-w-2xl text-center">
                  <p className="text-sm font-medium text-primary">Covis · Bug reporting</p>
                  <h1 className="mt-3 text-balance text-3xl font-bold tracking-tight text-foreground md:text-4xl lg:text-[2.5rem] lg:leading-tight">
                    Report bugs and check status without leaving the conversation
                  </h1>
                  <p className="mt-4 text-pretty text-base leading-relaxed text-muted-foreground md:text-lg">
                    Covis Assist is your front door to the Covis assistant—chat-first, API-backed, and
                    tuned for clear handoffs to engineering.
                  </p>
                  <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
                    <Button
                      asChild
                      size="lg"
                      className="h-12 min-w-[12rem] rounded-xl px-8 text-base shadow-md"
                    >
                      <Link href="/chat" className="gap-2">
                        Start chatting
                        <ArrowRight className="size-4" aria-hidden />
                      </Link>
                    </Button>
                    <Button asChild variant="outline" size="lg" className="h-12 rounded-xl px-6 text-base">
                      <Link href="/chat">Go to chat workspace</Link>
                    </Button>
                  </div>
                </div>

                <ul className="mx-auto mt-14 grid w-full max-w-3xl gap-6 md:mt-16 md:grid-cols-3 md:gap-6">
                  {features.map(({ icon: Icon, title, description }) => (
                    <li
                      key={title}
                      className="group rounded-2xl border border-border/80 bg-card/95 p-6 shadow-sm ring-1 ring-black/[0.03] motion-safe:transition-all motion-safe:duration-200 motion-safe:hover:-translate-y-0.5 motion-safe:hover:border-primary/20 motion-safe:hover:shadow-lg motion-safe:hover:ring-primary/15 dark:bg-card/80 dark:ring-white/[0.06] dark:motion-safe:hover:ring-primary/25"
                    >
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/12 text-primary motion-safe:transition-colors motion-safe:duration-200 motion-safe:group-hover:bg-primary/18">
                        <Icon className="size-5" aria-hidden />
                      </div>
                      <h2 className="mt-4 font-semibold text-foreground">{title}</h2>
                      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
                    </li>
                  ))}
                </ul>

                <p className="mt-auto border-t border-border/70 pt-8 text-center text-xs text-muted-foreground">
                  {BRAND_WORD_PRIMARY} {BRAND_WORD_ACCENT} — chat experience for Covis.
                </p>
          </div>
        </div>
      </main>
    </div>
  )
}
