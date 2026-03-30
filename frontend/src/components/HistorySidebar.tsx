import type { AskResult } from '../hooks/useAsk'

export interface HistoryEntry {
  query: string
  result: AskResult
}

interface Props {
  history: HistoryEntry[]
  selectedIndex: number | null
  onSelect: (index: number) => void
}

const CONFIDENCE_DOT: Record<string, string> = {
  high: 'bg-emerald-400',
  medium: 'bg-amber-400',
  low: 'bg-red-400',
}

export default function HistorySidebar({ history, selectedIndex, onSelect }: Props) {
  return (
    <aside className="w-72 shrink-0 border-r border-zinc-800 flex flex-col h-full">
      <div className="px-4 py-5 border-b border-zinc-800">
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">Session history</p>
        <p className="text-xs text-zinc-700 mt-1">Resets on page refresh</p>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {history.length === 0 ? (
          <p className="text-xs text-zinc-700 px-4 pt-4">Questions will appear here</p>
        ) : (
          [...history].reverse().map((entry, reversedIndex) => {
            const index = history.length - 1 - reversedIndex
            const isSelected = index === selectedIndex
            return (
              <button
                key={index}
                onClick={() => onSelect(index)}
                className={`w-full text-left px-4 py-3 border-b border-zinc-800/50 hover:bg-zinc-800/50 transition-colors group ${
                  isSelected ? 'bg-zinc-800' : ''
                }`}
              >
                <div className="flex items-start gap-2">
                  <span className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${CONFIDENCE_DOT[entry.result.confidence] ?? 'bg-zinc-600'}`} />
                  <p className={`text-xs leading-snug line-clamp-2 ${isSelected ? 'text-zinc-100' : 'text-zinc-400 group-hover:text-zinc-300'}`}>
                    {entry.query}
                  </p>
                </div>
              </button>
            )
          })
        )}
      </div>
    </aside>
  )
}
