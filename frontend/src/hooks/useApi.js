import { useState, useEffect } from 'react'

// In production (Vercel), VITE_API_URL is empty because vercel.json proxies
// /api/* to the Python backend. In local dev, vite.config.js proxy handles it.
const BASE_URL = import.meta.env.VITE_API_URL || ''

export default function useApi(endpoint) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch(`${BASE_URL}${endpoint}`)
      .then((res) => {
        if (!res.ok) throw new Error(`Error ${res.status}: ${res.statusText}`)
        return res.json()
      })
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [endpoint])

  return { data, loading, error }
}
