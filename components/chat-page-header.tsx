'use client'

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import { MessageSquare } from 'lucide-react'

export function ChatPageHeader() {
  return (
    <div className="shrink-0 px-4 pb-3 pt-5 md:px-8 md:pb-4 md:pt-6">
      <div className="relative mx-auto w-full max-w-3xl overflow-hidden rounded-2xl border border-border/70 bg-card/90 shadow-chat-card ring-1 ring-black/[0.03] backdrop-blur-sm dark:ring-white/[0.06]">
        <div
          className="absolute left-0 top-0 h-full w-1 bg-gradient-to-b from-primary via-primary/90 to-primary/60"
          aria-hidden
        />
        <div className="px-4 py-3.5 pl-6 md:px-5 md:py-4 md:pl-7">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/12 text-primary shadow-sm ring-1 ring-primary/10">
                <MessageSquare className="h-4 w-4" strokeWidth={2} aria-hidden />
              </div>
              <Breadcrumb>
                <BreadcrumbList className="text-xs text-muted-foreground sm:text-sm">
                  <BreadcrumbItem>
                    <BreadcrumbLink href="#" className="hover:text-foreground">
                      Home
                    </BreadcrumbLink>
                  </BreadcrumbItem>
                  <BreadcrumbSeparator />
                  <BreadcrumbItem>
                    <BreadcrumbPage className="font-normal text-muted-foreground">
                      Bug Reporting Chatbot
                    </BreadcrumbPage>
                  </BreadcrumbItem>
                </BreadcrumbList>
              </Breadcrumb>
            </div>
            <h1 className="mt-2.5 text-xl font-bold tracking-tight text-foreground md:text-2xl md:leading-tight lg:text-[1.6rem]">
              BUG REPORTING CHATBOT
            </h1>
            <p className="mt-1 max-w-2xl text-[13px] leading-snug text-muted-foreground sm:text-sm sm:leading-snug">
              Report bugs, create tasks, and check status in Covis — right from this conversation.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
