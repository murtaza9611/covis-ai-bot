import { NextResponse } from 'next/server'

const COVIS_QA_BASE = 'http://0.0.0.0:8569/api/v1/qa/sessions'

export const maxDuration = 120

type RouteContext = { params: Promise<{ id: string }> }

export async function POST(req: Request, context: RouteContext) {
  const { id } = await context.params

  let body: { message?: string; source?: string; cta_label?: string | null }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  const message = typeof body.message === 'string' ? body.message.trim() : ''
  if (!message) {
    return NextResponse.json({ error: 'message is required' }, { status: 400 })
  }

  const source = body.source === 'cta' ? 'cta' : 'text'
  const ctaLabel = typeof body.cta_label === 'string' ? body.cta_label : null

  try {
    const upstream = await fetch(`${COVIS_QA_BASE}/${id}/message`, {
      method: 'POST',
      headers: {
        accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message, source, cta_label: ctaLabel }),
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
