import { useState, useEffect, useCallback } from 'react'
import { API_BASE, getJSON, API_HINT } from '../api'

function PersonCard({ person }) {
    const [broken, setBroken] = useState(false)
    return (
        <div className="person-card">
            {broken ? (
                <div className="photo-missing">Photo file missing</div>
            ) : (
                <img src={`${API_BASE}${person.photo_url}`} alt={person.name} onError={() => setBroken(true)} />
            )}
            <p>{person.name}</p>
        </div>
    )
}

function PeoplePage() {
    const [people, setPeople] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    const [name, setName] = useState('')
    const [file, setFile] = useState(null)
    const [uploading, setUploading] = useState(false)
    const [uploadError, setUploadError] = useState(null)
    const [uploadSuccess, setUploadSuccess] = useState(null)

    const loadPeople = useCallback(() => {
        setLoading(true)
        getJSON('/people')
            .then((data) => {
                setPeople(data)
                setError(null)
            })
            .catch((err) => setError(err.message))
            .finally(() => setLoading(false))
    }, [])

    useEffect(() => {
        loadPeople()
    }, [loadPeople])

    const handleUpload = async (e) => {
        e.preventDefault()
        const form = e.currentTarget
        setUploadError(null)
        setUploadSuccess(null)

        if (!name.trim() || !file) {
            setUploadError('Both a name and a photo file are required.')
            return
        }

        setUploading(true)
        const formData = new FormData()
        formData.append('name', name.trim())
        formData.append('file', file)

        try {
            const res = await fetch(`${API_BASE}/people`, {
                method: 'POST',
                body: formData,
            })
            const data = await res.json().catch(() => ({}))

            if (!res.ok) {
                throw new Error(data.detail || `Upload failed (${res.status})`)
            }

            setUploadSuccess(`Registered '${data.name}' (face confidence: ${data.det_score.toFixed(3)})`)
            setName('')
            setFile(null)
            form.reset()
            loadPeople()
        } catch (err) {
            setUploadError(err.message === 'Failed to fetch' ? `Could not reach the API. ${API_HINT}` : err.message)
        } finally {
            setUploading(false)
        }
    }

    return (
        <div>
            <form className="card upload-form" onSubmit={handleUpload}>
                <h3>Register a new reference person</h3>
                <div className="upload-fields">
                    <input
                        type="text"
                        placeholder="Person's name"
                        aria-label="Person's name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                    />
                    <input
                        type="file"
                        aria-label="Reference photo"
                        accept="image/jpeg,image/png"
                        onChange={(e) => setFile(e.target.files[0] ?? null)}
                    />
                    <button className="btn" type="submit" disabled={uploading}>
                        {uploading ? 'Uploading...' : 'Register'}
                    </button>
                </div>
                {uploadError && <p className="upload-message error">{uploadError}</p>}
                {uploadSuccess && <p className="upload-message success">{uploadSuccess}</p>}
                <p className="upload-hint">
                    The photo must contain a clearly visible face. Registered people are matched on
                    the next pipeline run — a pipeline that's already running won't pick them up.
                </p>
            </form>

            <h3 className="section-title">Registered people ({people.length})</h3>
            {loading && <div className="status">Loading...</div>}
            {error && (
                <div className="status error">
                    <p>Failed to load people: {error}</p>
                    <p>{API_HINT}</p>
                </div>
            )}

            {!loading && !error && people.length === 0 && (
                <p className="status">No people registered yet — use the form above.</p>
            )}

            {!loading && !error && people.length > 0 && (
                <div className="people-grid">
                    {people.map((p) => <PersonCard key={p.id} person={p} />)}
                </div>
            )}
        </div>
    )
}

export default PeoplePage
