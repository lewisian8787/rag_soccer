import { useState } from 'react'
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
  const [collapsed, setCollapsed] = useState(true)

  return (
    <aside
      className={`${collapsed ? 'w-10' : 'w-72'} shrink-0 bg-[#040d07] border-r border-emerald-800 flex flex-col h-full transition-[width] duration-300 overflow-hidden`}
    >
      {collapsed ? (
        <div className="flex flex-col items-center h-full py-4 gap-4">
          <button
            onClick={() => setCollapsed(false)}
            aria-label="Expand session history"
            className="text-gray-500 hover:text-white transition-colors p-1 shrink-0"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
          <span className="text-gray-600 text-xs font-semibold uppercase tracking-widest [writing-mode:vertical-rl]">
            History
          </span>
        </div>
      ) : (
        <>
          <div className="px-4 py-5 border-b border-emerald-800 flex items-center justify-between shrink-0">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">Session history</p>
              <p className="text-xs text-gray-600 mt-1">Resets on page refresh</p>
            </div>
            <button
              onClick={() => setCollapsed(true)}
              aria-label="Collapse session history"
              className="text-gray-500 hover:text-white transition-colors shrink-0 p-1"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto py-2">
            {history.length === 0 ? (
              <p className="text-xs text-gray-600 px-4 pt-4">Questions will appear here</p>
            ) : (
              [...history].reverse().map((entry, reversedIndex) => {
                const index = history.length - 1 - reversedIndex
                const isSelected = index === selectedIndex
                return (
                  <button
                    key={index}
                    onClick={() => onSelect(index)}
                    className={`w-full text-left px-4 py-3 border-b border-[#1e3d28] hover:bg-[#162d1c] transition-colors group ${
                      isSelected ? 'bg-[#162d1c]' : ''
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <span className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${CONFIDENCE_DOT[entry.result.confidence] ?? 'bg-emerald-800'}`} />
                      <p className={`text-xs leading-snug line-clamp-2 ${isSelected ? 'text-white' : 'text-gray-400 group-hover:text-white'}`}>
                        {entry.query}
                      </p>
                    </div>
                  </button>
                )
              })
            )}
          </div>
        </>
      )}
    </aside>
  )
}
