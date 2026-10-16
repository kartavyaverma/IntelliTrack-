import { useState, useEffect, useCallback } from 'react'
import { API_BASE, getJSON, API_HINT } from '../api'
import { Icon, Status } from '../ui'

function PersonCard({ person }) {
    const [broken, setBroken] = useState(false)
    return (
        <figure className="panel person-card">
            {broken ? (
                <div className="photo-missing">Photo file missing</div>
            ) : (
                <img src={`${API_BASE}${person.photo_url}`} alt={person.name} onError={() => setBroken(true)} />
            )}
            <figcaption>
                {person.name}
                <span className="mono">ID {person.id}</span>
            </figcaption>
        </figure>
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
                const detail = typeof data.detail === 'string' ? data.detail : null
                throw new Error(detail || `Upload failed (${res.status})`)
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
            <form className="panel upload-panel" onSubmit={handleUpload}>
                <h2>Register a reference person</h2>
                <div className="upload-row">
                    <input
                        type="text"
                        placeholder="Person's name"
                        aria-label="Person's name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                    />
                    <label className={file ? 'dropzone has-file' : 'dropzone'}>
                        <Icon name="upload" size={16} />
                        <span className="file-name">{file ? file.name : 'Choose a JPG or PNG photo…'}</span>
                        <input
                            type="file"
                            aria-label="Reference photo"
                            accept="image/jpeg,image/png"
                            onChange={(e) => setFile(e.target.files[0] ?? null)}
                        />
                    </label>
                    <button className="btn" type="submit" disabled={uploading}>
                        {uploading ? 'Uploading…' : 'Register'}
                    </button>
                </div>
                {uploadError && <p className="upload-message error">{uploadError}</p>}
                {uploadSuccess && <p className="upload-message success">{uploadSuccess}</p>}
                <p className="upload-hint">
                    The photo must contain a clearly visible face. Registered people are matched on
                    the next pipeline run — a pipeline that's already running won't pick them up.
                </p>
            </form>

            <h2 className="section-title">
                Registered <span className="mono">({people.length})</span>
            </h2>
            {loading && <Status title="Loading…" />}
            {error && <Status kind="error" title={`Failed to load people: ${error}`}>{API_HINT}</Status>}

            {!loading && !error && people.length === 0 && (
                <Status title="No people registered yet">Use the form above to add one.</Status>
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
