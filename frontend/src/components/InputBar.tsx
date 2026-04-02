import { useState } from 'react'

interface Props {
  onAsk: (query: string) => void
  loading: boolean
  mode?: 'football' | 'fpl'
}

export default function InputBar({ onAsk, loading, mode = 'football' }: Props) {
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
      <label htmlFor="question-input" className="sr-only">
        Ask a question
      </label>
      <input
        id="question-input"
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={mode === 'fpl' ? 'e.g. Who should I captain this week?' : 'e.g. Who has been clinical up front recently?'}
        autoFocus
        disabled={loading}
        className="flex-1 bg-[#162b1f] border border-emerald-700/60 rounded-xl px-5 py-3.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-400 transition-colors shadow-[0_2px_24px_rgba(0,0,0,0.5)] disabled:opacity-50 disabled:cursor-not-allowed"
      />
      <button
        type="submit"
        disabled={!input.trim() || loading}
        aria-label="Submit question"
        className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-30 disabled:cursor-not-allowed text-zinc-950 text-sm font-bold px-6 py-3.5 rounded-xl transition-colors whitespace-nowrap"
      >
        Kick Off
      </button>
    </form>
  )
}
