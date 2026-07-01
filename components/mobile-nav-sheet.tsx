'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { PRIMARY_NAV } from '@/lib/nav-config'
import { cn } from '@/lib/utils'

type MobileNavSheetProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function MobileNavSheet({ open, onOpenChange }: MobileNavSheetProps) {
  const pathname = usePathname()

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="left"
        className="w-[min(100vw,20rem)] border-border/70 bg-card/85 p-0 shadow-2xl shadow-black/20 backdrop-blur-xl supports-[backdrop-filter]:bg-card/75"
      >
        <SheetHeader className="border-b border-border/70 bg-card/55 px-4 py-4 text-left backdrop-blur-sm">
          <SheetTitle className="text-base font-semibold text-foreground">
            Menu
          </SheetTitle>
        </SheetHeader>
        <div className="max-h-[calc(100vh-5rem)] overflow-y-auto p-4">
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
            {PRIMARY_NAV.map((item) => {
              const Icon = item.icon
              const active = item.href ? pathname === item.href : false
              const className = cn(
                'group flex min-h-[5.5rem] flex-col items-center justify-center gap-2 rounded-xl border px-2 py-3 text-center text-[11px] font-medium leading-tight motion-safe:transition-all motion-safe:duration-200',
                active
                  ? 'border-primary/25 bg-primary/10 text-primary shadow-md shadow-primary/10 ring-1 ring-primary/15'
                  : 'border-border/65 bg-card/70 text-muted-foreground shadow-sm hover:-translate-y-0.5 hover:border-primary/20 hover:bg-primary/[0.06] hover:text-foreground hover:shadow-md',
              )
              const inner = (
                <>
                  <div
                    className={cn(
                      'flex h-9 w-9 items-center justify-center rounded-lg',
                      active ? 'bg-primary/15' : 'bg-muted/60 group-hover:bg-primary/10',
                    )}
                  >
                    <Icon className="h-5 w-5 shrink-0" />
                  </div>
                  <span className="line-clamp-2 px-1">{item.label}</span>
                </>
              )

              return item.href ? (
                <Link
                  key={item.id}
                  href={item.href}
                  aria-current={active ? 'page' : undefined}
                  className={className}
                  onClick={() => onOpenChange(false)}
                >
                  {inner}
                </Link>
              ) : (
                <button
                  key={item.id}
                  type="button"
                  aria-current={active ? 'page' : undefined}
                  className={className}
                  onClick={() => onOpenChange(false)}
                >
                  {inner}
                </button>
              )
            })}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
