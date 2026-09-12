import { useEffect, useState, useCallback } from 'react'
import DomainPanel from './components/DomainPanel.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import { fetchDomains } from './services/api.js'
import './App.css'

export default function App() {
  const [domains, setDomains] = useState([])
  const [activeDomain, setActiveDomain] = useState('')
  const [domainsLoading, setDomainsLoading] = useState(true)

  const reloadDomains = useCallback(async () => {
    setDomainsLoading(true)
    try {
      const list = await fetchDomains()
      setDomains(list)
      // Keep the currently active domain selected if it still exists;
      // otherwise fall back to the first available one.
      setActiveDomain((prev) => {
        if (prev && list.some((d) => d.name === prev)) return prev
        return list[0]?.name || ''
      })
    } catch (err) {
      console.error('Failed to load domains', err)
    } finally {
      setDomainsLoading(false)
    }
  }, [])

  useEffect(() => {
    reloadDomains()
  }, [reloadDomains])

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="app-header__mark">§</span>
        <div>
          <h1>Domain Q&amp;A</h1>
          <p>Ask your notes questions. Every answer points back to its page.</p>
        </div>
      </header>

      <div className="app-body">
        <DomainPanel
          domains={domains}
          activeDomain={activeDomain}
          onSelectDomain={setActiveDomain}
          onUploaded={reloadDomains}
          loading={domainsLoading}
        />
        <ChatWindow activeDomain={activeDomain} />
      </div>
    </div>
  )
}
