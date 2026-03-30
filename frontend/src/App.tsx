import { useState } from 'react'
import { useAsk } from './hooks/useAsk'
import InputBar from './components/InputBar'
import AnswerCard from './components/AnswerCard'
import HistorySidebar from './components/HistorySidebar'
import type { HistoryEntry } from './components/HistorySidebar'

type Mode = 'football' | 'fpl'

function App() {
  const [mode, setMode] = useState<Mode>('football')
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  const { result, streamingText, loading, error, ask } = useAsk((r) => {
    setHistory(prev => {
      const next = [...prev, { query: r.query, result: r }]
      setSelectedIndex(next.length - 1)
      return next
    })
  })

  function handleAsk(query: string) {
    setSelectedIndex(null)
    ask(query, mode)
  }

  function handleModeChange(next: Mode) {
    setMode(next)
    setSelectedIndex(null)
    setHistory([])
  }

  const displayResult = selectedIndex !== null ? history[selectedIndex].result : result
  const hasContent = displayResult || loading || !!streamingText || !!error

  return (
    <div className="flex bg-zinc-950 text-zinc-100 min-h-screen">

      <HistorySidebar
        history={history}
        selectedIndex={selectedIndex}
        onSelect={setSelectedIndex}
      />

      <main className="flex-1 flex flex-col items-center px-4 -ml-72">
        <header className="mt-16 mb-12 text-center">
          <div className="flex items-center justify-center gap-3 mb-2">
            <span className="text-3xl">⚽</span>
            <h1 className="text-4xl font-black tracking-tight text-white">Football Form Guide</h1>
          </div>
          <p className="text-zinc-500 text-sm mb-6">Tactics, form, stats and fantasy — powered by match reports</p>

          {/* Mode toggle */}
          <div className="inline-flex rounded-xl border border-zinc-700 overflow-hidden">
            <button
              onClick={() => handleModeChange('football')}
              className={`px-5 py-2 text-sm font-semibold transition-colors ${
                mode === 'football'
                  ? 'bg-amber-500 text-zinc-950'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Football
            </button>
            <button
              onClick={() => handleModeChange('fpl')}
              className={`px-5 py-2 text-sm font-semibold transition-colors flex items-center gap-2 ${
                mode === 'fpl'
                  ? 'bg-purple-600 text-white'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              FPL
              <span className="text-xs font-bold px-1.5 py-0.5 rounded bg-purple-900 text-purple-300 border border-purple-700">
                BETA
              </span>
            </button>
          </div>
        </header>

        {hasContent && (
          <div className="w-full max-w-2xl mb-8">
            <AnswerCard
              result={displayResult}
              streamingText={streamingText}
              loading={loading}
              error={error}
            />
          </div>
        )}

        <div className="w-full max-w-2xl">
          {(history.length > 0) && !loading && (
            <p className="text-xs text-zinc-600 text-center mb-3 tracking-wide uppercase">
              Ask another question
            </p>
          )}
          <InputBar onAsk={handleAsk} loading={loading} mode={mode} />
        </div>
      </main>

    </div>
  )
}

export default App
