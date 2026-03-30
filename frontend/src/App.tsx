import { useState } from 'react'
import { useAsk } from './hooks/useAsk'
import InputBar from './components/InputBar'
import AnswerCard from './components/AnswerCard'
import HistorySidebar from './components/HistorySidebar'
import type { HistoryEntry } from './components/HistorySidebar'

function App() {
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
    ask(query)
  }

  // The result to display: selected history entry, or the live result
  const displayResult = selectedIndex !== null ? history[selectedIndex].result : result

  const hasContent = displayResult || loading || !!streamingText || !!error

  return (
    <div className="flex bg-zinc-950 text-zinc-100 min-h-screen">

      <HistorySidebar
        history={history}
        selectedIndex={selectedIndex}
        onSelect={setSelectedIndex}
      />

      <main className="flex-1 flex flex-col items-center px-4">
        <header className="mt-16 mb-12 text-center">
          <div className="flex items-center justify-center gap-3 mb-2">
            <span className="text-3xl">⚽</span>
            <h1 className="text-4xl font-black tracking-tight text-white">Football Form Guide</h1>
          </div>
          <p className="text-zinc-500 text-sm">Tactics, form, stats and fantasy — powered by match reports</p>
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
          <InputBar onAsk={handleAsk} loading={loading} />
        </div>
      </main>

    </div>
  )
}

export default App
