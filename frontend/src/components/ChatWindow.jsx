import { useEffect, useRef, useState } from 'react'
import MessageBubble from './MessageBubble.jsx'
import { askQuestion } from '../services/api.js'
import './ChatWindow.css'

export default function ChatWindow({ activeDomain }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isAsking, setIsAsking] = useState(false)
  const scrollRef = useRef(null)

  // Fresh conversation whenever the subject changes -- an answer about
  // DBMS shouldn't sit in the same thread as one about Compiler Design.
  useEffect(() => {
    setMessages([])
  }, [activeDomain])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  async function handleSubmit(e) {
    e.preventDefault()
    const question = input.trim()
    if (!question || isAsking) return

    if (!activeDomain) {
      setMessages((m) => [
        ...m,
        { role: 'user', content: question },
        { role: 'assistant', status: 'error', content: 'Upload a PDF into a subject first.' },
      ])
      setInput('')
      return
    }

    setMessages((m) => [
      ...m,
      { role: 'user', content: question },
      { role: 'assistant', status: 'loading' },
    ])
    setInput('')
    setIsAsking(true)

    try {
      const result = await askQuestion(activeDomain, question)
      setMessages((m) => [
        ...m.slice(0, -1),
        { role: 'assistant', content: result.answer, sources: result.sources },
      ])
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Something went wrong reaching the backend.'
      setMessages((m) => [...m.slice(0, -1), { role: 'assistant', status: 'error', content: detail }])
    } finally {
      setIsAsking(false)
    }
  }

  return (
    <main className="chat-window">
      <div className="chat-window__scroll" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="chat-window__empty">
            <p className="chat-window__empty-title">
              {activeDomain ? `Ask something about "${activeDomain}."` : 'No subject selected.'}
            </p>
            <p className="chat-window__empty-subtitle">
              {activeDomain
                ? 'Answers are grounded in the PDFs you\u2019ve uploaded, with sources cited below each reply.'
                : 'Upload a PDF on the left to create your first subject.'}
            </p>
          </div>
        ) : (
          messages.map((msg, i) => <MessageBubble key={i} {...msg} />)
        )}
      </div>

      <form className="chat-window__input-row" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={activeDomain ? `Ask about ${activeDomain}...` : 'Select a subject first...'}
          disabled={isAsking}
        />
        <button type="submit" disabled={isAsking || !input.trim()}>
          {isAsking ? 'Asking...' : 'Ask'}
        </button>
      </form>
    </main>
  )
}
