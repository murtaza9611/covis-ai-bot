'use client'

import { Bot } from 'lucide-react'
import type { SimpleChatMessage } from '@/lib/chat-mock'
import { getUserAvatarUrl } from '@/lib/user-avatar'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'

interface ChatMessageProps {
  message: SimpleChatMessage
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isBot = message.role === 'assistant'
  const text = message.text
  const isError = message.isError

  const motion =
    'motion-safe:animate-in motion-safe:fade-in motion-safe:zoom-in-95 motion-safe:slide-in-from-bottom-2 motion-safe:duration-300'

  if (isBot) {
    return (
      <div className={cn('group/msg mb-5 flex items-end gap-3', motion)}>
        <div
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary/25 to-primary/5 text-primary shadow-sm ring-2 ring-primary/10 motion-safe:transition-all motion-safe:duration-200 motion-safe:group-hover/msg:ring-primary/25 motion-safe:group-hover/msg:shadow-md"
          aria-hidden
        >
          <Bot className="h-5 w-5" strokeWidth={2} />
        </div>
        <div className="min-w-0 max-w-[min(90%,30rem)] flex-1">
          <p className="mb-1.5 pl-0.5 text-xs font-medium text-muted-foreground">Assistant</p>
          <div
            className={cn(
              'rounded-2xl rounded-tl-md border border-border bg-card/95 px-4 py-3 text-sm leading-relaxed text-card-foreground shadow-sm backdrop-blur-sm motion-safe:transition-all motion-safe:duration-200 motion-safe:group-hover/msg:shadow-md motion-safe:group-hover/msg:border-primary/20',
              isError &&
                'border-destructive/35 bg-destructive/[0.07] text-destructive motion-safe:group-hover/msg:border-destructive/40',
            )}
          >
            <p className="whitespace-pre-wrap break-words text-inherit">{text}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('group/msg mb-5 flex flex-row-reverse items-end gap-3', motion)}>
      <Avatar className="h-10 w-10 shrink-0 ring-2 ring-primary/15 motion-safe:transition-transform motion-safe:duration-200 motion-safe:group-hover/msg:ring-primary/30 motion-safe:group-hover/msg:scale-[1.02]">
        <AvatarImage src={getUserAvatarUrl()} alt="" width={40} height={40} />
        <AvatarFallback className="bg-gradient-to-br from-primary/20 to-primary/5 text-sm font-semibold text-primary">
          You
        </AvatarFallback>
      </Avatar>
      <div className="min-w-0 max-w-[min(90%,30rem)] flex-1 flex justify-end">
        <div>
          <p className="mb-1.5 pr-0.5 text-right text-xs font-medium text-muted-foreground">
            You
          </p>
          <div className="rounded-2xl rounded-tr-md bg-gradient-to-br from-primary via-primary to-primary/95 px-4 py-3 text-sm leading-relaxed text-primary-foreground shadow-md motion-safe:transition-all motion-safe:duration-200 motion-safe:group-hover/msg:shadow-lg motion-safe:group-hover/msg:brightness-[1.03]">
            <p className="whitespace-pre-wrap break-words text-left">{text}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
