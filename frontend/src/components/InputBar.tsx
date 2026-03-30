import { useState } from 'react'

interface Props {
  onAsk: (query: string) => void
  loading: boolean
}

export default function InputBar({ onAsk, loading }: Props) {
  const [input, setInput] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const q = input.trim()
    if (!q || loading) return
    onAsk(q)
    setInput('')
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-3">
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="e.g. Who has been clinical up front recently?"
        autoFocus
        className="flex-1 bg-zinc-900 border border-zinc-700 rounded-xl px-5 py-3.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-amber-500 transition-colors"
      />
      <button
        type="submit"
        disabled={!input.trim() || loading}
        className="bg-amber-500 hover:bg-amber-400 disabled:opacity-30 disabled:cursor-not-allowed text-zinc-950 text-sm font-bold px-6 py-3.5 rounded-xl transition-colors whitespace-nowrap"
      >
        Kick Off
      </button>
    </form>
  )
}
