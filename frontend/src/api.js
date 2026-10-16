// Single place for the backend address, shared by every page.
export const API_BASE = 'http://127.0.0.1:8000'

export async function getJSON(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`API returned ${res.status}`)
  return res.json()
}

export const API_HINT =
  'Check that the API is running (uvicorn src.api.main:app --reload) on port 8000.'
