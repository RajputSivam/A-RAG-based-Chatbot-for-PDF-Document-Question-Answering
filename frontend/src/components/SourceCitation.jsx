import { useState } from 'react'
import './SourceCitation.css'

export default function SourceCitation({ sources }) {
  const [expandedIndex, setExpandedIndex] = useState(null)

  if (!sources || sources.length === 0) return null

  return (
    <div className="citations">
      <p className="citations__label">Sources</p>
      <ul className="citations__list">
        {sources.map((src, i) => {
          const isOpen = expandedIndex === i
          return (
            <li key={i} className="citation">
              <button
                className="citation__header"
                onClick={() => setExpandedIndex(isOpen ? null : i)}
                aria-expanded={isOpen}
              >
                <span className="citation__index">[{i + 1}]</span>
                <span className="citation__file">{src.source_file}</span>
                {src.page_number != null && (
                  <span className="citation__page">p.{src.page_number}</span>
                )}
                <span className="citation__score">
                  {Math.round(src.similarity_score * 100)}% match
                </span>
              </button>
              {isOpen && <p className="citation__excerpt">{src.content}</p>}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
