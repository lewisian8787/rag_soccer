import { useStandings } from '../hooks/useStandings'

interface Props {
  onTeamClick: (query: string) => void
}

export default function StandingsTable({ onTeamClick }: Props) {
  const { standings, loading, error } = useStandings()

  return (
    <aside
      aria-label="Premier League table"
      className="w-72 shrink-0 border-l border-zinc-800 flex flex-col h-full overflow-y-auto"
    >
      <div className="px-4 py-5 border-b border-zinc-800 shrink-0">
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">PL Table</p>
        <p className="text-xs text-zinc-700 mt-1">Select a team to find out how they've been playing</p>
      </div>

      {loading && (
        <p className="text-xs text-zinc-600 px-4 pt-4">Loading...</p>
      )}

      {error && (
        <p className="text-xs text-red-500 px-4 pt-4">Could not load table</p>
      )}

      {!loading && !error && (
        <table className="w-full table-fixed text-xs" role="table">
          <colgroup>
            <col className="w-7" />
            <col />
            <col className="w-8" />
            <col className="w-9" />
          </colgroup>
          <thead>
            <tr className="text-zinc-600 border-b border-zinc-800">
              <th scope="col" className="pl-3 py-2 text-left font-medium">#</th>
              <th scope="col" className="px-1 py-2 text-left font-medium">Team</th>
              <th scope="col" className="px-1 py-2 text-center font-medium">GD</th>
              <th scope="col" className="pr-3 pl-1 py-2 text-center font-semibold text-zinc-400">Pts</th>
            </tr>
          </thead>
          <tbody>
            {standings.map((row, i) => (
              <tr
                key={row.team}
                className="border-b border-zinc-800/50 hover:bg-zinc-800/50 transition-colors"
              >
                <td className="pl-3 py-2 text-zinc-600 tabular-nums">{i + 1}</td>
                <td className="px-1 py-2">
                  <button
                    onClick={() => onTeamClick(`Tell me about ${row.team}'s season so far`)}
                    className="text-left text-zinc-300 hover:text-white transition-colors w-full truncate block"
                  >
                    {row.team}
                  </button>
                </td>
                <td className="px-1 py-2 text-center text-zinc-500 tabular-nums">
                  {row.gd > 0 ? `+${row.gd}` : row.gd}
                </td>
                <td className="pr-3 pl-1 py-2 text-center font-semibold text-zinc-200 tabular-nums">{row.pts}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </aside>
  )
}
