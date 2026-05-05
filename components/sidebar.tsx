'use client'

import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import { ACTIVE_PRIMARY_NAV_ID, PRIMARY_NAV } from '@/lib/nav-config'
import { TooltipContent, TooltipProvider } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

export function Sidebar({ className }: { className?: string }) {
  return (
    <aside
      className={cn(
        'flex h-full min-h-0 w-[3.25rem] shrink-0 flex-col overflow-x-hidden rounded-3xl bg-sidebar/80 px-1 py-4 shadow-md shadow-black/[0.04] backdrop-blur-md dark:bg-sidebar/70 dark:shadow-black/20',
        className,
      )}
    >
      <TooltipProvider delayDuration={200}>
        <nav
          className="flex min-h-0 flex-1 flex-col gap-2 overflow-x-hidden overflow-y-auto"
          aria-label="Primary"
        >
          {PRIMARY_NAV.map((item) => {
            const Icon = item.icon
            const active = item.id === ACTIVE_PRIMARY_NAV_ID
            return (
              <TooltipPrimitive.Root key={item.id}>
                <TooltipPrimitive.Trigger asChild>
                  <button
                    type="button"
                    aria-current={active ? 'page' : undefined}
                    aria-label={item.label}
                    className={cn(
                      'group flex size-10 shrink-0 items-center justify-center rounded-2xl motion-safe:transition-all motion-safe:duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-sidebar',
                      active
                        ? 'bg-secondary text-primary shadow-sm motion-safe:hover:bg-secondary'
                        : 'text-sidebar-foreground hover:bg-primary/12 hover:text-primary motion-safe:hover:scale-[1.04] motion-safe:active:scale-[0.98] dark:hover:bg-muted/60 dark:hover:text-foreground',
                    )}
                  >
                    <Icon
                      className={cn(
                        'h-[1.35rem] w-[1.35rem] shrink-0',
                        active
                          ? 'text-primary'
                          : 'text-sidebar-foreground group-hover:text-primary dark:group-hover:text-foreground',
                      )}
                      aria-hidden
                    />
                  </button>
                </TooltipPrimitive.Trigger>
                <TooltipContent side="right" sideOffset={10} className="font-medium">
                  {item.label}
                </TooltipContent>
              </TooltipPrimitive.Root>
            )
          })}
        </nav>
      </TooltipProvider>
    </aside>
  )
}
