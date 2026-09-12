import { useRef, useState } from 'react'
import { uploadDocument } from '../services/api.js'
import './DomainPanel.css'

export default function DomainPanel({ domains, activeDomain, onSelectDomain, onUploaded, loading }) {
  const [newDomainName, setNewDomainName] = useState(
    () => window.localStorage.getItem('rag-pending-domain') || ''
  )
  const [isDragging, setIsDragging] = useState(false)
  const [uploadState, setUploadState] = useState({ status: 'idle', progress: 0, message: '' })
  const fileInputRef = useRef(null)

  // The domain a file gets uploaded to: whatever the user typed in the "new
  // subject" box takes priority (so typing + dropping a file in one motion
  // works), otherwise the currently selected domain.
  const targetDomain = newDomainName.trim() || activeDomain

  async function handleFiles(files) {
    const file = files?.[0]
    if (!file) return

    if (!targetDomain) {
      setUploadState({ status: 'error', progress: 0, message: 'Name a subject/domain first.' })
      return
    }
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadState({ status: 'error', progress: 0, message: 'Only PDF files are supported.' })
      return
    }

    setUploadState({ status: 'uploading', progress: 0, message: `Indexing ${file.name}...` })
    try {
      const result = await uploadDocument(targetDomain, file, (pct) =>
        setUploadState((s) => ({ ...s, progress: pct }))
      )
      setUploadState({ status: 'success', progress: 100, message: result.message })
      setNewDomainName('')
      window.localStorage.removeItem('rag-pending-domain')
      onSelectDomain(result.domain)
      onUploaded()
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Upload failed. Is the backend running?'
      setUploadState({ status: 'error', progress: 0, message: detail })
    }
  }

  return (
    <aside className="domain-panel">
      <section className="domain-panel__section">
        <h2>Subjects</h2>
        {loading ? (
          <p className="domain-panel__hint">Loading...</p>
        ) : domains.length === 0 ? (
          <p className="domain-panel__hint">
            No subjects yet. Upload a PDF below to create your first one.
          </p>
        ) : (
          <ul className="domain-panel__list">
            {domains.map((d) => (
              <li key={d.name}>
                <button
                  className={`domain-panel__item ${d.name === activeDomain ? 'is-active' : ''}`}
                  onClick={() => onSelectDomain(d.name)}
                >
                  <span>{d.name}</span>
                  <span className="domain-panel__count">{d.chunk_count}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="domain-panel__section">
        <h2>Add material</h2>
        <label className="domain-panel__label" htmlFor="new-domain">
          Subject name
        </label>
        <input
          id="new-domain"
          type="text"
          placeholder={activeDomain || 'e.g. Compiler Design'}
          value={newDomainName}
          onChange={(e) => {
            const value = e.target.value
            setNewDomainName(value)
            if (value.trim()) window.localStorage.setItem('rag-pending-domain', value)
            else window.localStorage.removeItem('rag-pending-domain')
            setUploadState((state) =>
              state.status === 'error' ? { status: 'idle', progress: 0, message: '' } : state
            )
          }}
        />

        <div
          className={`dropzone ${isDragging ? 'is-dragging' : ''}`}
          onDragOver={(e) => {
            e.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setIsDragging(false)
            handleFiles(e.dataTransfer.files)
          }}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            hidden
            onChange={(e) => handleFiles(e.target.files)}
          />
          <p className="dropzone__title">Drop a PDF here</p>
          <p className="dropzone__subtitle">or click to browse</p>
        </div>

        {uploadState.status === 'uploading' && (
          <div className="upload-progress">
            <div className="upload-progress__bar" style={{ width: `${uploadState.progress}%` }} />
            <span>{uploadState.message}</span>
          </div>
        )}
        {uploadState.status === 'success' && (
          <p className="upload-feedback upload-feedback--success">{uploadState.message}</p>
        )}
        {uploadState.status === 'error' && (
          <p className="upload-feedback upload-feedback--error">{uploadState.message}</p>
        )}
      </section>
    </aside>
  )
}
