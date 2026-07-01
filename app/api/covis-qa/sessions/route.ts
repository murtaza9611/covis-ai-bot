import { NextResponse } from 'next/server'

const COVIS_QA_URL = 'http://0.0.0.0:8569/api/v1/qa/sessions'

export const maxDuration = 120

export async function POST(req: Request) {
  let body: { mode?: string; drive_mode?: string; max_turns?: number; timezone?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  const mode = body.mode === 'NEGATIVE' ? 'NEGATIVE' : 'POSITIVE'
  const drive_mode = body.drive_mode === 'MANUAL' ? 'MANUAL' : 'AUTO'
  const max_turns =
    typeof body.max_turns === 'number' && body.max_turns >= 1 && body.max_turns <= 30
      ? body.max_turns
      : 10
  const timezone =
    typeof body.timezone === 'string' && body.timezone ? body.timezone : 'UTC'

  try {
    const upstream = await fetch(COVIS_QA_URL, {
      method: 'POST',
      headers: {
        accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ mode, drive_mode, max_turns, timezone }),
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
            typeof json === 'object' && json !== null && 'message' in json
              ? String((json as { message: unknown }).message)
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
