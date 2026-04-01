import { useState } from 'react'
import { useAsk } from './hooks/useAsk'
import InputBar from './components/InputBar'
import AnswerCard from './components/AnswerCard'
import HistorySidebar from './components/HistorySidebar'
import type { HistoryEntry } from './components/HistorySidebar'
import StandingsTable from './components/StandingsTable'

type Mode = 'football' | 'fpl'

const EXAMPLE_QUESTIONS: Record<Mode, { label: string; type: 'stats' | 'rag' }[]> = {
  football: [
    { label: 'Who are the top scorers this season?', type: 'stats' },
    { label: "How does Arsenal play out from the back?", type: 'rag' },
    { label: 'Which team has the best defensive record?', type: 'stats' },
    { label: "What's Liverpool's pressing style like?", type: 'rag' },
    { label: "Who has the most assists this season?", type: 'stats' },
    { label: 'How have Chelsea been performing recently?', type: 'rag' },
  ],
  fpl: [
    { label: 'Who should I captain this week?', type: 'stats' },
    { label: 'Best budget midfielder under £6m?', type: 'stats' },
    { label: 'Who are the best differentials right now?', type: 'stats' },
    { label: 'Which players have the easiest fixtures?', type: 'stats' },
    { label: 'Who is injured or doubtful this week?', type: 'stats' },
    { label: 'Who has been the best value this season?', type: 'stats' },
  ],
}

function App() {
  const [mode, setMode] = useState<Mode>('football')
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [currentQuery, setCurrentQuery] = useState('')

  const { result, streamingText, loading, error, ask } = useAsk((r) => {
    setHistory(prev => {
      const next = [...prev, { query: r.query, result: r }]
      setSelectedIndex(next.length - 1)
      return next
    })
  })

  function handleAsk(query: string) {
    setSelectedIndex(null)
    setCurrentQuery(query)
    ask(query, mode)
  }

  function handleModeChange(next: Mode) {
    setMode(next)
    setSelectedIndex(null)
    setHistory([])
  }

  const displayResult = selectedIndex !== null ? history[selectedIndex].result : result
  const displayQuery = selectedIndex !== null ? history[selectedIndex].result.query : currentQuery
  const hasContent = displayResult || loading || !!streamingText || !!error

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-950 text-zinc-100">

      <HistorySidebar
        history={history}
        selectedIndex={selectedIndex}
        onSelect={setSelectedIndex}
      />

      <main className="flex-1 overflow-y-auto flex flex-col items-center px-4">
        <header className="mt-16 mb-12 text-center">
          <div className="flex items-center justify-center gap-3 mb-2">
            <span className="text-3xl">⚽</span>
            <h1 className="text-4xl font-black tracking-tight text-white">Football Form Guide</h1>
          </div>
          <p className="text-zinc-500 text-sm mb-6">Tactics, form, stats and maybe fantasy — powered by match reports</p>

          {/* Mode toggle */}
          <div role="group" aria-label="Mode" className="inline-flex rounded-xl border border-zinc-700 overflow-hidden">
            <button
              onClick={() => handleModeChange('football')}
              aria-pressed={mode === 'football'}
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
              aria-pressed={mode === 'fpl'}
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
          <div className="w-full max-w-2xl mb-8 flex flex-col gap-4">
            {displayQuery && (
              <div className="flex justify-end">
                <div className="bg-zinc-800 text-zinc-100 text-sm px-5 py-3 rounded-2xl rounded-tr-sm max-w-[80%]">
                  {displayQuery}
                </div>
              </div>
            )}
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

        {!hasContent && (
          <div className="w-full max-w-2xl mt-10">
            <p className="text-xs text-zinc-600 uppercase tracking-wide mb-4">Try asking</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUESTIONS[mode].map(({ label, type }) => (
                <button
                  key={label}
                  onClick={() => handleAsk(label)}
                  className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-600 text-zinc-400 hover:text-zinc-200 text-sm transition-colors"
                >
                  <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${type === 'stats' ? 'bg-amber-500' : 'bg-sky-500'}`} />
                  {label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-4 mt-4">
              <span className="flex items-center gap-1.5 text-xs text-zinc-600">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500" /> Stats
              </span>
              <span className="flex items-center gap-1.5 text-xs text-zinc-600">
                <span className="w-1.5 h-1.5 rounded-full bg-sky-500" /> Match reports
              </span>
            </div>
          </div>
        )}
        <div className="pb-16" />
      </main>

      <StandingsTable onTeamClick={handleAsk} />

    </div>
  )
}

export default App
