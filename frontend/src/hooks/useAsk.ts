import { useState } from 'react'

export interface AskResult {
  answer: string
  confidence: 'high' | 'medium' | 'low'
  sources: { title: string; published_at: string }[]
  caveat: string | null
  query: string
  query_types: string[]
  retrieval_scores: number[]
}

export function useAsk(onResult?: (r: AskResult) => void) {
  const [result, setResult] = useState<AskResult | null>(null)
  const [streamingText, setStreamingText] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function ask(query: string) {
    setLoading(true)
    setStreamingText('')
    setResult(null)
    setError(null)

    try {
      const res = await fetch('/api/ask/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
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
            setStreamingText(accumulatedAnswer)
          } else if (event.type === 'done') {
            const r: AskResult = {
              answer: accumulatedAnswer,
              confidence: event.confidence,
              sources: event.sources ?? [],
              caveat: event.caveat ?? null,
              query,
              query_types: [],
              retrieval_scores: [],
            }
            setResult(r)
            setStreamingText('')
            onResult?.(r)
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return { result, streamingText, loading, error, ask }
}
