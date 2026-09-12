// Thin wrapper around the backend API. Keeping all fetch/axios calls in one
// place means components stay focused on rendering, and the base URL only
// needs to change in one spot if you deploy the backend elsewhere.
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const client = axios.create({ baseURL: BASE_URL })

export async function fetchDomains() {
  const { data } = await client.get('/api/domains')
  return data
}

export async function uploadDocument(domain, file, onProgress) {
  const formData = new FormData()
  formData.append('domain', domain)
  formData.append('file', file)

  const { data } = await client.post('/api/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (evt) => {
      if (onProgress && evt.total) {
        onProgress(Math.round((evt.loaded * 100) / evt.total))
      }
    },
  })
  return data
}

export async function askQuestion(domain, question) {
  const { data } = await client.post('/api/ask', { domain, question })
  return data
}
