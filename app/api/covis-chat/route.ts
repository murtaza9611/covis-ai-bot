import { NextResponse } from 'next/server'

// const COVIS_CHAT_URL = 'https://ai-bot.covis.ai/api/v1/chat'
const COVIS_CHAT_URL = 'http://0.0.0.0:8569/api/v1/chat'

export const maxDuration = 60

export async function POST(req: Request) {
  let body: { message?: string; timezone?: string; session_id?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  const message = typeof body.message === 'string' ? body.message : ''
  const timezone =
    typeof body.timezone === 'string' && body.timezone
      ? body.timezone
      : 'UTC'
  const session_id =
    typeof body.session_id === 'string' && body.session_id
      ? body.session_id
      : '1'

  if (!message.trim()) {
    return NextResponse.json({ error: 'message is required' }, { status: 400 })
  }

  try {
    const upstream = await fetch(COVIS_CHAT_URL, {
      method: 'POST',
      headers: {
        accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message, timezone, session_id }),
      signal: req.signal,
    })

    const text = await upstream.text()
    let json: unknown = null
    try {
      json = text ? JSON.parse(text) : null
    } catch {
      json = { raw: text }
    }

    if (!upstream.ok) {
      return NextResponse.json(
        {
          error:
            typeof json === 'object' && json !== null && 'error' in json
              ? String((json as { error: unknown }).error)
              : text || upstream.statusText,
        },
        { status: upstream.status },
      )
    }

    return NextResponse.json(json ?? {})
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Upstream request failed'
    return NextResponse.json({ error: msg }, { status: 502 })
  }
}
