import { useEffect, useState } from 'react'

export interface StandingRow {
  team: string
  played: number
  won: number
  drawn: number
  lost: number
  gf: number
  ga: number
  gd: number
  pts: number
}

export function useStandings() {
  const [standings, setStandings] = useState<StandingRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/standings')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(setStandings)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return { standings, loading, error }
}
