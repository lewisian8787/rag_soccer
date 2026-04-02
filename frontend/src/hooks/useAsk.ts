import { useState } from 'react'

export interface ConversationTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface AskResult {
  answer: string
  confidence: number
  sources: { title: string; published_at: string }[]
  caveat: string | null
  query: string
  query_types: string[]
  retrieval_scores: number[]
}

export function useAsk() {
  const [result, setResult] = useState<AskResult | null>(null)
  const [fullText, setFullText] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function ask(
    query: string,
    mode: 'football' | 'fpl' = 'football',
    history: ConversationTurn[] = []
  ) {
    setLoading(true)
    setFullText('')
    setResult(null)
    setError(null)

    try {
      const res = await fetch('/api/ask/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, mode, history }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail ?? `HTTP ${res.status}`)
      }

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulatedAnswer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''

        for (const part of parts) {
          if (!part.startsWith('data: ')) continue
          const event = JSON.parse(part.slice(6))

          if (event.type === 'error') {
            throw new Error(event.message ?? 'Stream error from server')
          } else if (event.type === 'token') {
            accumulatedAnswer += event.text
            setFullText(accumulatedAnswer)
          } else if (event.type === 'done') {
            const r: AskResult = {
              answer: accumulatedAnswer,
              confidence: event.confidence,
              sources: event.sources ?? [],
              caveat: event.caveat ?? null,
              query,
              query_types: event.query_types ?? [],
              retrieval_scores: event.retrieval_scores ?? [],
            }
            console.group(`[FFG] ${query}`)
            console.log('Pipeline:', r.query_types.join(' + ') || 'unknown')
            console.log('Confidence:', r.confidence)
            if (r.retrieval_scores.length) console.log('Retrieval scores:', r.retrieval_scores)
            if (r.caveat) console.log('Caveat:', r.caveat)
            console.groupEnd()
            setResult(r)
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  function clearFullText() {
    setFullText('')
    setResult(null)
  }

  return { result, fullText, loading, error, ask, clearFullText }
}
