import { useEffect, useRef, useState } from 'react'
import type { AskResult } from '../hooks/useAsk'

interface Props {
  result: AskResult | null
  streamingText: string
  loading: boolean
  error: string | null
}

const CONFIDENCE_STYLES = {
  high: 'text-emerald-400 border-emerald-700 bg-emerald-950',
  medium: 'text-amber-400 border-amber-700 bg-amber-950',
  low: 'text-red-400 border-red-700 bg-red-950',
}

const CONFIDENCE_DOT = {
  high: 'bg-emerald-400',
  medium: 'bg-amber-400',
  low: 'bg-red-400',
}

const RENDER_INTERVAL_MS = 50

export default function AnswerCard({ result, streamingText, loading, error }: Props) {
  const [displayedText, setDisplayedText] = useState('')
  const pendingRef = useRef('')

  // Accumulate incoming tokens in a ref, flush to display every RENDER_INTERVAL_MS.
  // This gives a smooth readable pace without the queue-buildup of char-by-char animation.
  useEffect(() => {
    pendingRef.current = streamingText
  }, [streamingText])

  useEffect(() => {
    if (!loading) {
      setDisplayedText('')
      pendingRef.current = ''
      return
    }
    const interval = setInterval(() => {
      if (pendingRef.current !== displayedText) {
        setDisplayedText(pendingRef.current)
      }
    }, RENDER_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [loading])

  if (error) {
    return (
      <div role="alert" className="rounded-2xl border border-red-800 bg-red-950 px-7 py-5 text-sm text-red-300">
        {error}
      </div>
    )
  }

  if (loading && !streamingText) {
    return (
      <div aria-live="polite" aria-label="Analysing" className="rounded-2xl border border-emerald-700/60 bg-[#162b1f] shadow-[0_2px_24px_rgba(0,0,0,0.5)] px-7 py-8 flex items-center gap-3">
        <span aria-hidden="true" className="text-2xl motion-safe:animate-bounce" style={{ animationDuration: '0.8s' }}>⚽</span>
        <span className="text-gray-400 text-sm">Analysing...</span>
      </div>
    )
  }

  if (loading && displayedText) {
    return (
      <div aria-live="polite" className="rounded-2xl border border-emerald-700/60 bg-[#162b1f] shadow-[0_2px_24px_rgba(0,0,0,0.5)] px-7 py-6">
        <p className="text-white leading-relaxed whitespace-pre-wrap">
          {displayedText}
          <span aria-hidden="true" className="motion-safe:animate-bounce inline-block" style={{ animationDuration: '0.8s' }}> ⚽</span>
        </p>
      </div>
    )
  }

  if (!result) return null

  const confStyle = CONFIDENCE_STYLES[result.confidence] ?? CONFIDENCE_STYLES.low
  const dotStyle = CONFIDENCE_DOT[result.confidence] ?? CONFIDENCE_DOT.low

  return (
    <div aria-live="polite" className="rounded-2xl border border-emerald-700/60 bg-[#162b1f] shadow-[0_2px_24px_rgba(0,0,0,0.5)] overflow-hidden">
      <div className="px-7 py-5">
        <p className="text-white leading-relaxed whitespace-pre-wrap">{result.answer}</p>
      </div>
      <div className="px-7 pb-5 flex flex-col gap-3">
        <span className={`inline-flex items-center gap-1.5 text-xs font-semibold w-fit px-3 py-1 rounded-full border ${confStyle}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${dotStyle}`} />
          {result.confidence} confidence
        </span>
        {result.caveat && (
          <p className="text-xs text-amber-400 leading-relaxed border-l-2 border-amber-600 pl-3">
            {result.caveat}
          </p>
        )}
      </div>
    </div>
  )
}
