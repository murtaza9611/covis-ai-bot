import { NextResponse } from 'next/server'

const COVIS_QA_BASE = 'http://0.0.0.0:8569/api/v1/qa/sessions'

export const maxDuration = 120

type RouteContext = { params: Promise<{ id: string }> }

export async function POST(_req: Request, context: RouteContext) {
  const { id } = await context.params

  try {
    const upstream = await fetch(`${COVIS_QA_BASE}/${id}/stop`, {
      method: 'POST',
      headers: { accept: 'application/json' },
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
