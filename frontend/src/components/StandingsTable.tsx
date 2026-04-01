import { useState } from 'react'
import { useStandings } from '../hooks/useStandings'

interface Props {
  onTeamClick: (query: string) => void
}

export default function StandingsTable({ onTeamClick }: Props) {
  const [collapsed, setCollapsed] = useState(true)
  const { standings, loading, error } = useStandings()

  return (
    <aside
      aria-label="Premier League table"
      className={`${collapsed ? 'w-10' : 'w-72'} shrink-0 bg-[#040d07] border-l border-emerald-800 flex flex-col h-full transition-[width] duration-300 overflow-hidden`}
    >
      {collapsed ? (
        <div className="flex flex-col items-center h-full py-4 gap-4">
          <button
            onClick={() => setCollapsed(false)}
            aria-label="Expand Premier League table"
            className="text-gray-500 hover:text-white transition-colors p-1 shrink-0"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
          <span className="text-gray-600 text-xs font-semibold uppercase tracking-widest [writing-mode:vertical-rl]">
            PL Table
          </span>
        </div>
      ) : (
        <>
          <div className="px-4 py-5 border-b border-emerald-800 shrink-0 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-400">PL Table</p>
              <p className="text-xs text-gray-600 mt-1">Select a team to find out how they've been playing</p>
            </div>
            <button
              onClick={() => setCollapsed(true)}
              aria-label="Collapse Premier League table"
              className="text-gray-500 hover:text-white transition-colors shrink-0 p-1"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>

          {loading && <p className="text-xs text-gray-500 px-4 pt-4">Loading...</p>}
          {error && <p className="text-xs text-red-500 px-4 pt-4">Could not load table</p>}

          {!loading && !error && (
            <table className="w-full table-fixed text-xs" role="table">
              <colgroup>
                <col className="w-7" />
                <col />
                <col className="w-8" />
                <col className="w-9" />
              </colgroup>
              <thead>
                <tr className="text-gray-500 border-b border-emerald-800">
                  <th scope="col" className="pl-3 py-2 text-left font-medium">#</th>
                  <th scope="col" className="px-1 py-2 text-left font-medium">Team</th>
                  <th scope="col" className="px-1 py-2 text-center font-medium">GD</th>
                  <th scope="col" className="pr-3 pl-1 py-2 text-center font-semibold text-gray-300">Pts</th>
                </tr>
              </thead>
              <tbody>
                {standings.map((row, i) => (
                  <tr key={row.team} className="border-b border-[#1e3d28] hover:bg-[#162d1c] transition-colors">
                    <td className="pl-3 py-2 text-gray-600 tabular-nums">{i + 1}</td>
                    <td className="px-1 py-2">
                      <button
                        onClick={() => onTeamClick(`Tell me about ${row.team}'s season so far`)}
                        className="text-left text-gray-300 hover:text-white transition-colors w-full truncate block"
                      >
                        {row.team}
                      </button>
                    </td>
                    <td className="px-1 py-2 text-center text-gray-500 tabular-nums">
                      {row.gd > 0 ? `+${row.gd}` : row.gd}
                    </td>
                    <td className="pr-3 pl-1 py-2 text-center font-semibold text-white tabular-nums">{row.pts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </aside>
  )
}
