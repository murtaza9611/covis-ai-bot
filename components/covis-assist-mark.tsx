import { cn } from '@/lib/utils'

/** Navbar / favicon mark: conversation bubble + tri-dot thread (bug-report chat). */
export function CovisAssistMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={cn('shrink-0', className)}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <path
        fill="currentColor"
        d="M6.75 4.5h10.5A3.75 3.75 0 0 1 21 8.25v5.25a3.75 3.75 0 0 1-3.75 3.75h-6.88l-4.12 3.09V17.25h-.75A3.75 3.75 0 0 1 3 13.5V8.25A3.75 3.75 0 0 1 6.75 4.5Z"
      />
      <circle cx="9" cy="11.25" r="1.35" className="fill-primary" />
      <circle cx="12" cy="11.25" r="1.35" className="fill-primary" />
      <circle cx="15" cy="11.25" r="1.35" className="fill-primary" />
    </svg>
  )
}
