import SourceCitation from './SourceCitation.jsx'
import './MessageBubble.css'

export default function MessageBubble({ role, content, sources, status }) {
  const isUser = role === 'user'

  return (
    <div className={`message ${isUser ? 'message--user' : 'message--assistant'}`}>
      <div className="message__bubble">
        {status === 'loading' ? (
          <div className="message__typing">
            <span />
            <span />
            <span />
          </div>
        ) : status === 'error' ? (
          <p className="message__error">{content}</p>
        ) : (
          <p className="message__text">{content}</p>
        )}
        {status !== 'loading' && !isUser && <SourceCitation sources={sources} />}
      </div>
    </div>
  )
}
