import { useEffect, useRef, useState } from 'react'
import type { AskResult } from '../hooks/useAsk'

interface Props {
  result: AskResult | null
  fullText: string
  loading: boolean
  error: string | null
  onAnimationComplete?: (result: AskResult) => void
}

const CHARS_PER_TICK = 2
const TICK_MS = 60

function ConfidenceSlider({ score }: { score: number }) {
  const pct = ((score - 1) / 9) * 100

  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs text-gray-500">
        <span>cold</span>
        <span>hot</span>
      </div>
      <div className="relative h-2 rounded-full overflow-hidden" style={{
        background: 'linear-gradient(to right, #3b82f6, #06b6d4, #84cc16, #f59e0b, #ef4444)'
      }}>
        <div
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-white shadow-md -translate-x-1/2"
          style={{ left: `${pct}%`, background: `hsl(${220 - pct * 2.2}deg 90% 55%)` }}
        />
      </div>
    </div>
  )
}

export default function AnswerCard({ result, fullText, loading, error, onAnimationComplete }: Props) {
  const [displayedLength, setDisplayedLength] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const fullTextRef = useRef(fullText)
  fullTextRef.current = fullText

  // Unmount cleanup
  useEffect(() => {
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [])

  useEffect(() => {
    if (!fullText) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      setDisplayedLength(0)
      return
    }

    if (intervalRef.current) return // already animating, interval chases fullTextRef naturally

    setDisplayedLength(0)
    intervalRef.current = setInterval(() => {
      setDisplayedLength(prev => {
        const next = Math.min(prev + CHARS_PER_TICK, fullTextRef.current.length)
        if (next >= fullTextRef.current.length) {
          clearInterval(intervalRef.current!)
          intervalRef.current = null
        }
        return next
      })
    }, TICK_MS)
  }, [fullText])

  // Fire onAnimationComplete when animation catches up and stream is done
  useEffect(() => {
    if (result && fullText && displayedLength >= fullText.length) {
      onAnimationComplete?.(result)
    }
  }, [displayedLength, fullText, result])

  const displayedText = fullText.slice(0, displayedLength)
  const isAnimating = fullText.length > 0 && displayedLength < fullText.length

  if (error) {
    return (
      <div role="alert" className="rounded-2xl border border-red-800 bg-red-950 px-7 py-5 text-sm text-red-300">
        {error}
      </div>
    )
  }

  if (loading && !fullText) {
    return (
      <div aria-live="polite" aria-label="Analysing" className="rounded-2xl border border-emerald-700/60 bg-[#162b1f] shadow-[0_2px_24px_rgba(0,0,0,0.5)] px-7 py-8 flex items-center gap-3">
        <span aria-hidden="true" className="text-2xl motion-safe:animate-bounce" style={{ animationDuration: '0.8s' }}>⚽</span>
        <span className="text-gray-400 text-sm">Analysing...</span>
      </div>
    )
  }

  if (isAnimating || (loading && fullText)) {
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

  return (
    <div aria-live="polite" className="rounded-2xl border border-emerald-700/60 bg-[#162b1f] shadow-[0_2px_24px_rgba(0,0,0,0.5)] overflow-hidden">
      <div className="px-7 py-5">
        <p className="text-white leading-relaxed whitespace-pre-wrap">{result.answer}</p>
      </div>
      <div className="px-7 pb-5 flex flex-col gap-3">
        <ConfidenceSlider score={result.confidence} />
        {result.caveat && (
          <p className="text-xs text-amber-400 leading-relaxed border-l-2 border-amber-600 pl-3">
            {result.caveat}
          </p>
        )}
      </div>
    </div>
  )
}
