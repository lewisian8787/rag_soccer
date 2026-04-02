import { useState, useRef, useEffect } from 'react'
import { useAsk, type ConversationTurn, type AskResult } from './hooks/useAsk'
import InputBar from './components/InputBar'
import AnswerCard from './components/AnswerCard'
import HistorySidebar from './components/HistorySidebar'
import type { HistoryEntry } from './components/HistorySidebar'
import StandingsTable from './components/StandingsTable'

type Mode = 'football' | 'fpl'

const MAX_HISTORY_TURNS = 10

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
  const [history, setHistory] = useState<HistoryEntry[][]>([[]])
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [currentQuery, setCurrentQuery] = useState('')
  const [conversationHistory, setConversationHistory] = useState<ConversationTurn[]>([])
  const [activeHistory, setActiveHistory] = useState<HistoryEntry[]>([])
  const activeQueryRef = useRef<HTMLDivElement>(null)
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  const { fullText, result, loading, error, ask, clearFullText } = useAsk()

  function handleAnimationComplete(r: AskResult) {
    clearFullText()
    const entry = { query: r.query, result: r }
    setActiveHistory(prev => [...prev, entry])
    setHistory(prev => {
      const next = [...prev]
      next[next.length - 1] = [...next[next.length - 1], entry]
      setSelectedIndex(next.filter(c => c.length > 0).length - 1)
      return next
    })
    setConversationHistory(prev => {
      const updated = [...prev,
        { role: 'user' as const, content: r.query },
        { role: 'assistant' as const, content: r.answer },
      ]
      const maxMessages = MAX_HISTORY_TURNS * 2
      return updated.length > maxMessages ? updated.slice(updated.length - maxMessages) : updated
    })
  }

  useEffect(() => {
    if (loading) {
      requestAnimationFrame(() => {
        activeQueryRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
    }
  }, [loading])

  function handleAsk(query: string) {
    setSelectedIndex(null)
    setCurrentQuery(query)
    ask(query, mode, conversationHistory)
  }

  function handleModeChange(next: Mode) {
    setMode(next)
    setSelectedIndex(null)
    setHistory([[]])
    setConversationHistory([])
  }

  function handleNewConversation() {
    setActiveHistory([])
    setConversationHistory([])
    setSelectedIndex(null)
    clearFullText()
    setHistory(prev => [...prev, []])
  }

  const hasContent = activeHistory.length > 0 || loading || !!fullText || !!error

  return (
    <div className="flex h-screen overflow-hidden pitch-bg text-white">

      <HistorySidebar
        history={history}
        selectedIndex={selectedIndex}
        onSelect={setSelectedIndex}
      />

      <main className="flex-1 flex flex-col">
        <header className="mt-10 mb-30 text-center px-4 shrink-0">
          <div className="flex flex-col items-center mb-3">
            <button onClick={handleNewConversation} aria-label="New conversation">
              <img src="/logos/dugout-green.png" alt="The Dugout" className="w-40 h-auto object-contain hover:opacity-80 transition-opacity" />
            </button>
            <p className="text-gray-500 text-sm mt-1">Tactics, form, stats and maybe fantasy — powered by match reports</p>
          </div>

          {/* Mode toggle */}
          <div role="group" aria-label="Mode" className="inline-flex rounded-xl border border-[#2a5438] overflow-hidden">
            <button
              onClick={() => handleModeChange('football')}
              aria-pressed={mode === 'football'}
              className={`px-5 py-2 text-sm font-semibold transition-colors ${
                mode === 'football'
                  ? 'bg-emerald-500 text-zinc-950'
                  : 'text-gray-400 hover:text-white'
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
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              FPL
              <span className="text-xs font-bold px-1.5 py-0.5 rounded bg-purple-900 text-purple-300 border border-purple-700">
                BETA
              </span>
            </button>
          </div>
        </header>

        {/* Scrollable conversation area */}
        <div className="flex-1 flex flex-col items-center px-4 py-2 min-h-0">
          {hasContent && (
            <div ref={scrollAreaRef} className="w-full max-w-2xl mb-4 flex flex-col gap-4 overflow-y-auto">
            {activeHistory.map((entry, i) => (
              <div key={i} className="flex flex-col gap-4">
                <div className="flex justify-end">
                  <div className="bg-[#1e3d2a] border border-emerald-700/60 text-white text-sm px-5 py-3 rounded-2xl rounded-tr-sm max-w-[80%] shadow-[0_2px_16px_rgba(0,0,0,0.4)]">
                    {entry.query}
                  </div>
                </div>
                <AnswerCard
                  result={entry.result}
                  fullText=""
                  loading={false}
                  error={null}
                />
              </div>
            ))}
            {(loading || fullText) && (
              <div ref={activeQueryRef} className="flex flex-col gap-4">
                <div className="flex justify-end">
                  <div className="bg-[#1e3d2a] border border-emerald-700/60 text-white text-sm px-5 py-3 rounded-2xl rounded-tr-sm max-w-[80%] shadow-[0_2px_16px_rgba(0,0,0,0.4)]">
                    {currentQuery}
                  </div>
                </div>
                <AnswerCard
                  result={result}
                  fullText={fullText}
                  loading={loading}
                  error={error}
                  onAnimationComplete={handleAnimationComplete}
                />
              </div>
            )}
            <div />
            </div>
          )}

          {!hasContent && (
            <div className="w-full max-w-2xl">
              <div className="mb-8">
                <InputBar onAsk={handleAsk} onNewConversation={handleNewConversation} loading={loading} hasContent={hasContent} mode={mode} />
              </div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-4">Try asking</p>
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_QUESTIONS[mode].map(({ label, type }) => (
                  <button
                    key={label}
                    onClick={() => handleAsk(label)}
                    className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[#162b1f] border border-emerald-700/60 hover:border-emerald-400 text-gray-300 hover:text-white text-sm transition-colors shadow-[0_1px_8px_rgba(0,0,0,0.3)]"
                  >
                    <span className="flex-shrink-0 text-xs">{type === 'stats' ? '📊' : '📰'}</span>
                    {label}
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-4 mt-4">
                <span className="flex items-center gap-1.5 text-xs text-gray-500">
                  <span>📊</span> Stats
                </span>
                <span className="flex items-center gap-1.5 text-xs text-gray-500">
                  <span>📰</span> Match reports
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Fixed input bar at bottom — only during conversation */}
        {hasContent && (
          <div className="shrink-0 w-full px-4 pb-10 flex flex-col items-center">
            {(history.length > 0) && !loading && (
              <p className="text-xs text-gray-500 text-center mb-3 tracking-wide uppercase">
                Ask another question
              </p>
            )}
            <div className="w-full max-w-2xl">
              <InputBar onAsk={handleAsk} onNewConversation={handleNewConversation} loading={loading} hasContent={hasContent} mode={mode} />
            </div>
          </div>
        )}
      </main>

      <StandingsTable onTeamClick={handleAsk} disabled={loading} />

    </div>
  )
}

export default App
