'use client'

import Markdown from 'react-markdown'
import { cn } from '@/lib/utils'

type ChatMarkdownProps = {
  content: string
  className?: string
}

export function ChatMarkdown({ content, className }: ChatMarkdownProps) {
  return (
    <div className={cn('chat-markdown break-words text-inherit', className)}>
      <Markdown
        components={{
        p: ({ children }) => (
          <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-foreground">{children}</strong>
        ),
        ol: ({ children }) => (
          <ol className="my-3 list-decimal space-y-3 pl-5 marker:text-muted-foreground">
            {children}
          </ol>
        ),
        ul: ({ children }) => (
          <ul className="my-3 list-disc space-y-2 pl-5 marker:text-muted-foreground">
            {children}
          </ul>
        ),
        li: ({ children }) => (
          <li className="leading-relaxed pl-0.5 pb-0.5">{children}</li>
        ),
        em: ({ children }) => <em className="italic">{children}</em>,
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-primary underline underline-offset-2 hover:text-primary/80"
          >
            {children}
          </a>
        ),
      }}
      >
        {content}
      </Markdown>
    </div>
  )
}
