import { useEffect, useRef, useState } from 'react'
import type { AskResult } from '../hooks/useAsk'

interface Props {
  result: AskResult | null
  streamingText: string
  loading: boolean
  error: string | null
}

const CHAR_DELAY_MS = 28 // ms per character — raise to slow down, lower to speed up

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

export default function AnswerCard({ result, streamingText, loading, error }: Props) {
  // targetRef holds the latest full text received — even after streamingText clears on `done`
  const targetRef = useRef('')
  const [displayedText, setDisplayedText] = useState('')

  const isTyping = displayedText.length < targetRef.current.length

  // Update target as new tokens arrive
  useEffect(() => {
    if (streamingText) targetRef.current = streamingText
  }, [streamingText])

  // Reset when a new question is asked (loading starts, no text yet)
  useEffect(() => {
    if (loading && !streamingText) {
      targetRef.current = ''
      setDisplayedText('')
    }
  }, [loading, streamingText])

  // Typewriter: advance one character at a time
  useEffect(() => {
    if (displayedText.length >= targetRef.current.length) return
    const timer = setTimeout(() => {
      setDisplayedText(targetRef.current.slice(0, displayedText.length + 1))
    }, CHAR_DELAY_MS)
    return () => clearTimeout(timer)
  }, [displayedText, streamingText]) // streamingText dep re-triggers when target grows

  if (error) {
    return (
      <div className="rounded-2xl border border-red-800 bg-red-950 px-7 py-5 text-sm text-red-300">
        {error}
      </div>
    )
  }

  // Soccer ball while waiting for first token
  if (loading && !streamingText && !displayedText) {
    return (
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900 px-7 py-8 flex items-center gap-3">
        <span className="text-2xl animate-bounce" style={{ animationDuration: '0.8s' }}>⚽</span>
        <span className="text-zinc-500 text-sm">Analysing...</span>
      </div>
    )
  }

  // Typewriter in progress — show typed text, cursor while still going
  if (isTyping || (!result && displayedText)) {
    return (
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900 px-7 py-6">
        <p className="text-zinc-100 leading-relaxed whitespace-pre-wrap">
          {displayedText}
          {isTyping && <span className="animate-bounce inline-block" style={{ animationDuration: '0.8s' }}> ⚽</span>}
        </p>
      </div>
    )
  }

  if (!result) return null

  const confStyle = CONFIDENCE_STYLES[result.confidence] ?? CONFIDENCE_STYLES.low
  const dotStyle = CONFIDENCE_DOT[result.confidence] ?? CONFIDENCE_DOT.low

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900 overflow-hidden">

      <div className="px-7 py-5">
        <p className="text-zinc-100 leading-relaxed whitespace-pre-wrap">{result.answer}</p>
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
